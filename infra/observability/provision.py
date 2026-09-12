#!/usr/bin/env python3
"""Provision private Wardrub analytics + monitoring using the active gcloud user.

No third-party dependencies. Defaults to a read-only plan; --apply makes changes.
"""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = "gen-lang-client-0842206246"
RAW = "wardrub_events"
REPORTING = "wardrub_reporting"
SINK = "wardrub-product-events"
SCHEMA = "wardrub_product_v1"


def request(method, url, body=None, *, allow=()):
    req = urllib.request.Request(url, method=method, headers={
        "Authorization": f"Bearer {TOKEN}", "x-goog-user-project": PROJECT,
        "Content-Type": "application/json",
    }, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.load(response) if response.status != 204 else {}
    except urllib.error.HTTPError as exc:
        if exc.code in allow:
            return None
        raise RuntimeError(f"{method} {url}: {exc.code} {exc.read().decode()}") from exc


def dataset(name, raw=False):
    base = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/datasets"
    if not request("GET", f"{base}/{name}", allow=(404,)):
        body = {"datasetReference": {"projectId": PROJECT, "datasetId": name},
                "location": "US", "description": "Private Wardrub product telemetry; no image data"}
        if raw:
            body["defaultPartitionExpirationMs"] = str(180 * 86400 * 1000)
        request("POST", base, body)
    # These dedicated datasets are owner-only, not shared with project-wide viewers.
    current = request("GET", f"{base}/{name}")
    access = [entry for entry in current.get("access", []) if "specialGroup" not in entry]
    patch = {"access": access}
    if raw:
        patch["defaultPartitionExpirationMs"] = str(180 * 86400 * 1000)
    request("PATCH", f"{base}/{name}", patch)


def grant_sink(writer):
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/datasets/{RAW}"
    current = request("GET", url)
    access = current.get("access", [])
    grant = {"role": "WRITER", "userByEmail": writer.removeprefix("serviceAccount:")}
    if grant not in access:
        # New Logging service agents can take a short time to propagate to IAM.
        for attempt in range(4):
            try:
                request("PATCH", url, {"access": access + [grant]})
                break
            except RuntimeError as exc:
                if "does not exist" not in str(exc) or attempt == 3:
                    raise
                time.sleep(15)


def monitoring():
    base = f"https://monitoring.googleapis.com/v3/projects/{PROJECT}"
    dashboard = json.loads(Path(__file__).with_name("dashboard.json").read_text())
    url = f"https://monitoring.googleapis.com/v1/projects/{PROJECT}/dashboards"
    name = f"projects/{PROJECT}/dashboards/wardrub-operations"
    existing = request("GET", f"https://monitoring.googleapis.com/v1/{name}", allow=(404,))
    dashboard["name"] = name
    if existing:
        dashboard["etag"] = existing["etag"]
        request("PATCH", f"https://monitoring.googleapis.com/v1/{name}", dashboard)
    else:
        request("POST", url, dashboard)
    checks = request("GET", f"{base}/uptimeCheckConfigs").get("uptimeCheckConfigs", [])
    check = next((x for x in checks if x["displayName"] == "Wardrub API liveness"), None)
    if not check:
        check = request("POST", f"{base}/uptimeCheckConfigs", {
            "displayName": "Wardrub API liveness",
            "monitoredResource": {"type": "uptime_url", "labels": {
                "project_id": PROJECT, "host": "wardrub-api-1028744939274.us-central1.run.app"}},
            "httpCheck": {"path": "/health", "port": 443, "useSsl": True,
                          "validateSsl": True, "requestMethod": "GET"},
            "timeout": "10s", "period": "300s", "checkerType": "STATIC_IP_CHECKERS",
        })
    channels = request("GET", f"{base}/notificationChannels").get("notificationChannels", [])
    channel = next((c for c in channels if c.get("type") == "email" and c.get("labels", {}).get("email_address") == args.email), None)
    if not channel:
        channel = request("POST", f"{base}/notificationChannels", {
            "type": "email", "displayName": "Wardrub owner",
            "labels": {"email_address": args.email}, "enabled": True,
        })
    policies = request("GET", f"{base}/alertPolicies").get("alertPolicies", [])
    check_id = check["name"].rsplit("/", 1)[-1]
    definitions = [
        ("Wardrub API liveness failing", {
            "filter": f'metric.type="monitoring.googleapis.com/uptime_check/check_passed" AND resource.type="uptime_url" AND metric.label.check_id="{check_id}"',
            "comparison": "COMPARISON_GT", "thresholdValue": 1, "duration": "300s",
            "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_NEXT_OLDER", "crossSeriesReducer": "REDUCE_COUNT_FALSE"}],
        }),
        ("Wardrub API elevated 5xx", {
            "filter": 'metric.type="run.googleapis.com/request_count" AND resource.type="cloud_run_revision" AND resource.label.service_name="wardrub-api" AND metric.label.response_code_class="5xx"',
            "comparison": "COMPARISON_GT", "thresholdValue": 0.0166667, "duration": "300s",
            "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_RATE", "crossSeriesReducer": "REDUCE_SUM"}],
        }),
    ]
    for title, threshold in definitions:
        policy = {"displayName": title, "combiner": "OR", "enabled": True,
                  "notificationChannels": [channel["name"]],
                  "conditions": [{"displayName": title, "conditionThreshold": threshold}],
                  "alertStrategy": {"autoClose": "1800s"},
                  "documentation": {"mimeType": "text/markdown", "content": "Inspect Wardrub Cloud Run revisions and request logs. /health is liveness only, not Firestore/Gemini readiness. Do not expose user data in incident reports."}}
        existing = next((p for p in policies if p["displayName"] == title), None)
        if existing:
            policy["name"] = existing["name"]
            request("PATCH", "https://monitoring.googleapis.com/v3/" + existing["name"], policy)
        else:
            request("POST", f"{base}/alertPolicies", policy)
    print("Monitoring: https://console.cloud.google.com/monitoring/dashboards/custom/wardrub-operations?project=" + PROJECT)
    print("Notification channel:", channel["name"], channel.get("verificationStatus", "unspecified"))


def views():
    sql = Path(__file__).with_name("views.sql").read_text()
    # Each statement is independently retryable. Maximum scan cap protects setup costs.
    for statement in sql.split(";"):
        if not statement.strip():
            continue
        job = request("POST", f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/queries", {
            "query": statement, "useLegacySql": False, "location": "US",
            "maximumBytesBilled": "1000000000", "timeoutMs": 20000,
        })
        while not job.get("jobComplete"):
            time.sleep(2)
            job = request("GET", f'https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/queries/{job["jobReference"]["jobId"]}?location=US')
        if job.get("errors"):
            raise RuntimeError(job["errors"])
    print("Looker Studio: connect BigQuery →", PROJECT, "→", REPORTING)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--email", help="Private owner email for Monitoring alerts")
    parser.add_argument("--billing-only", action="store_true", help="Prepare a private dataset for the owner to enable Billing export in the console")
    parser.add_argument("--views-only", action="store_true", help="Create views after the first exported event creates the raw table")
    args = parser.parse_args()
    if not args.apply:
        print("Plan: US BigQuery raw dataset (180-day partition retention), reporting views, narrowly filtered Logging sink + dataset-only writer IAM; private Monitoring dashboard, 5-minute API uptime check, liveness and 5xx email alerts. BigQuery queries and uptime checks may incur usage costs. No public grants or app data changes.")
        raise SystemExit(0)
    account = subprocess.check_output(["gcloud", "config", "get-value", "account"], text=True).strip()
    if account != "hardikuppal.hu@gmail.com":
        raise SystemExit("Refusing to use a non-Wardrub gcloud account")
    TOKEN = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    if args.billing_only:
        dataset("wardrub_billing")
        print("Private wardrub_billing dataset ready. Enable Standard usage cost export in Cloud Billing → Billing export → BigQuery export. This does not enable the export automatically.")
        raise SystemExit(0)
    if args.views_only:
        views()
        raise SystemExit(0)
    if not args.email:
        parser.error("--email is required with --apply")
    dataset(RAW, raw=True)
    dataset(REPORTING)
    sink_url = f"https://logging.googleapis.com/v2/projects/{PROJECT}/sinks"
    body = {"name": SINK,
            "destination": f"bigquery.googleapis.com/projects/{PROJECT}/datasets/{RAW}",
            "filter": f'resource.type="cloud_run_revision" AND resource.labels.service_name="wardrub-api" AND jsonPayload.event_schema="{SCHEMA}"',
            "bigqueryOptions": {"usePartitionedTables": True}}
    existing = request("GET", sink_url + "/" + SINK, allow=(404,))
    sink = request("PUT" if existing else "POST", sink_url + ("/" + SINK if existing else "") + "?uniqueWriterIdentity=true", body)
    grant_sink(sink["writerIdentity"])
    monitoring()
    print("Sink ready. Deploy product events, then run --apply --views-only after export creates the raw table.")
