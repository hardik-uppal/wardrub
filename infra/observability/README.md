# Wardrub analytics and operations — MVP

Issue #10. This directory provisions only the personal project
`gen-lang-client-0842206246`, never the Aftershoot project.

## Deployment

```sh
python3 infra/observability/provision.py  # read-only plan
python3 infra/observability/provision.py --apply --email YOUR_OWNER_EMAIL
# Deploy the product-event code through the normal PR/release workflow.
# Once the first matching log entry creates the raw BigQuery table:
python3 infra/observability/provision.py --apply --views-only
```

Requires a logged-in personal gcloud account with BigQuery dataset creation,
Logging sink administration and Monitoring administration. Tokens are read into
process memory; no service-account keys are created. Reruns update the named
resources; unrelated resources are untouched. A freshly created Logging service
agent may need a short IAM propagation delay. The sink writer gets dataset-only
write access, not project-wide BigQuery permissions.

Resources:

- `wardrub_events` (US): partitioned Cloud Run stdout table, **180-day** default
  partition retention, private owner + sink writer access.
- `wardrub_reporting` (US): three aggregate SQL views, no UID/email columns.
- `wardrub-product-events`: sink restricted to the Wardrub service and
  `jsonPayload.event_schema="wardrub_product_v1"`; excludes general application logs.
- Monitoring dashboard ID `wardrub-operations`: request rate, 5xx rate, P95
  latency by revision, container instances.
- Public HTTPS `/health` uptime check every five minutes.
- Email alerts: liveness failure from more than one checker for five minutes;
  sustained 5xx rate above ~5 errors per five minutes for five minutes.

BigQuery storage/queries and uptime checks can incur charges. Logical views scan
at most 180 days of the small filtered raw dataset. There is no automatic billing
cap. Do not enable rapid auto-refresh or public report sharing. Start with daily
report usage; review BigQuery jobs and GCP billing before expanding.

## Create the Looker Studio report (browser step)

Looker Studio report layout creation requires the owner browser; this repository
cannot create a report URL through the available tools. Provisioned data sources
are ready to connect once views exist.

1. Open https://lookerstudio.google.com/ using the personal project owner account.
2. Create → Report → Add data → BigQuery → My Projects.
3. Select `gen-lang-client-0842206246` → `wardrub_reporting` → `daily_activity`.
4. Title: **Wardrub — Activity & Journey Health**. Keep report sharing restricted.
5. Add a date control (last 28 days), and a time series with `day` and
   `observed_active_users`; a second time series can show `magazine_users`.
6. Add `daily_magazine` as a data source; create scorecards using SUM of `requests`,
   `generations`, `cache_hits`, `failures`, and `below_garment_threshold`.
7. Add `daily_milestones`; create a table grouped by `day` and `event_name` showing
   `event_count` and `unique_users`.
8. Use the owner's credentials and keep sharing owner-only. Adding another viewer
   requires a deliberate privacy/access review. Never connect the raw events table.
9. Add a text note with the deployment date: **Observed activity starts with this
   release; no historical activity has been reconstructed.**

Do NOT sum daily distinct users and label the result MAU/WAU. A date-range sum is
user-days, not distinct people. The MVP is milestone counts, not a cohort funnel.
Cross-day distinct users, cohort retention and account-readiness snapshots need
separate aggregate queries and collection work.

## Cost dashboard: actual spend comes first

The connected GCP project has billing enabled, but no billing export dataset was
found in this project during setup. Activity logs cannot establish actual spend.

```sh
python3 infra/observability/provision.py --apply --billing-only
```

Owner browser step: Cloud Billing → select the linked billing account → Billing
export → BigQuery export → enable **Standard usage cost** in project
`gen-lang-client-0842206246`, dataset `wardrub_billing`. Do not move/disable an
existing export in another project without checking first. Enabling export is a
console operation; creating the dataset alone does not enable it. Billing may take
hours or longer to populate and historical coverage depends on export configuration.

After the source table exists, run `billing_views.sql` in BigQuery (US location).
SQL is not validated against live billing data until the export exists. Standard
export is sufficient for this MVP; detailed resource export is optional, not needed.

Looker report's first page should be **Spend**:

- MTD net cost (sum `net_cost`, date control this month), separated by currency.
- Daily net-cost time series, breakdown by service.
- Service cost table: Gemini/Vertex, Cloud Run, Storage, BigQuery, Monitoring, etc.
- Credits and last-export timestamp; show delayed/missing data as unknown, not zero.
- Invoice-month reconciliation from `monthly_invoice_cost`, distinct from usage-day
  reporting. Project-filtered totals may exclude account-level taxes/adjustments.

The application uses a Gemini API key when present. Its key-owning project must be
verified before claiming this billing export covers Gemini spend; configuration
alone is not proof. FAL charges are external and are NOT included in GCP billing.
Add a separate provider cost source or explicit excluded-cost note. Per-feature
cost (Magazine versus try-on) requires measured tokens/images/retries and versioned
pricing estimates, reconciled against billing; it cannot be inferred from event
counts alone. Do not label these estimates as actual charges.

Budgets send notifications, not hard caps. Pick a monthly budget and thresholds
before creating one. Keep automatic dashboard refresh conservative and review the
dashboard's own BigQuery/Monitoring costs. No billing export, budget, or actual
cost total is claimed until separately verified.

## Product dashboard (registrations, activity, readiness)

Run `schema.sql`, then `product_views.sql` in BigQuery US after provisioning the
private datasets. Refresh inventory with `python3 infra/observability/user_snapshot.py
--apply` (personal gcloud account). The script reads account/metadata/object names,
never image bytes, and stores only aggregate counters and signup-day totals. No
UID or email is stored in snapshots. An entire completed snapshot is inserted as
one row; partial read failure prevents publishing. Existing snapshot freshness is
visible in the report. Firestore reads span collections, not one consistent transaction.

Looker Studio → Add data → BigQuery → `wardrub_reporting`:

- `registration_summary`: scorecards for total_registered, with_avatar,
  with_any_garment, with_ten_garments, with_profile, with_saved_magazine. Use MAX,
  not SUM across refreshes. Include snapshot_time/snapshot_age_hours prominently.
- `registrations_by_day`: time series signup_day / registered_accounts. Counts
  creation dates of currently existing Auth accounts (including disabled), not
  deleted accounts or an immutable historical registration ledger.
- `active_user_summary`: DAU, rolling 7-day WAU and rolling 30-day MAU including
  today (IST calendar days). Actual distinct UIDs across each window, never sums
  of daily distincts. Values are NULL while there are no observed events. Show
  coverage_status and last_observed_event. These fixed-window scorecards don't
  respond to arbitrary date controls. Recent deployments have incomplete coverage.
- `daily_milestones`, `daily_magazine`, `daily_activity`: event volumes and daily
  observed users. These only populate after deployment plus successful sink delivery.

Readiness counts are independent current-state stages, NOT an ordered conversion
funnel. Disabled accounts are excluded from readiness but included in registered.
`ten_garments_without_saved_magazine` means no persisted feed was found, not a
proven failure. Explicit color/fit stage counts do not infer legacy analysis state.
An actual ordered funnel, cohort retention, per-success cost, and dedicated
style-completion events remain follow-up work.

Automated refresh preparation: `bash infra/observability/deploy_snapshot.sh --apply`
builds a dedicated metadata-only Cloud Run Job and six-hour Scheduler trigger.
Runtime has Auth/Firestore read, object-list (NOT image-read), BigQuery job execution
and only analytics-dataset write access. Cloud Build and Scheduler add potential
usage charges. The first deployment attempt was blocked by Cloud Build
PERMISSION_DENIED before job/schedule creation. The dataset and manual snapshot
are live; automatic refresh is NOT yet running. Do not silently broaden the
collector's permissions to work around build/deployment permissions.

No Looker Studio report layout or report URL has been created by these scripts.
The owner must add these sources/charts in the browser and keep sharing restricted.

## Metric definitions and limitations

- Observed active users: distinct authenticated UIDs emitting any instrumented
  event on an IST calendar day. `profile_loaded` covers authenticated app bootstrap
  and Profile refresh, NOT every navigation or tab that remains open overnight.
- Client milestones are best-effort and deduplicated per UID/browser. Clearing
  storage or switching devices can emit them again; not authoritative first-ever
  account actions. Sign-in events are not account-created events.
- Magazine requests include GET and explicit regeneration. Cache hits and generations
  are separate. A generated event means the service returned a feed and its existing
  save method reported success, NOT an independent audit of durable persistence.
- Failures are caught endpoint errors. Timeouts/terminated instances may produce no
  product failure event; Cloud Run 5xx metrics remain the operational complement.
- Events may arrive late and Cloud Logging can redeliver. Views deduplicate by
  `insertId`; the same business action in two distinct events is not deduplicated.
- Inventory snapshots and registration creation dates are available, but no historical
  activity backfill, measured model cost attribution, retention cohorts, precise
  session tracking, or automatic report layout is included in this MVP.
- `/health` is liveness only. It does not certify Firestore, GCS, or Gemini readiness.
- The synthetic `telemetry_probe` entry has an empty user ID and is excluded from
  all aggregate views. It verifies plumbing, never user activity.

## Security, retention and deletion

Product event records have only event name, authenticated UID, server timestamp,
release revision, schema version and optional numeric garment count. Client-supplied
names outside the activation allowlist are rejected. Free-text properties, emails,
photos, URLs, prompts, model output, tokens and locations are not exported.

UIDs are still personal data: keep raw access restricted. BigQuery dataset ACLs
cannot override inherited project-level administrators. Do not add broad project
roles for report viewers. General app logs are outside this sink and retain their
existing access/retention policy.

On a user deletion request, resolve the UID through the restricted Auth admin
interface and delete matching records from the raw table using a parameterized
BigQuery DELETE. The views recompute automatically. Delete their product data and
Auth account through the separate account-deletion procedure as well. BigQuery time
travel/fail-safe copies and Logging retention may retain data temporarily under
Google's retention semantics; do not promise immediate physical erasure. Analytics
export for a user must use an owner-only UID-filtered query, not a public dashboard.

## Verification and rollback

- Run `python -m unittest discover -s backend/tests` in the isolated test environment
  and `npm test` / `npm run lint` in frontend.
- Rerun provisioning to check idempotency, inspect dataset ACLs and partition expiry.
- Verify a real authenticated action yields allowlisted JSON stdout, then a raw row.
- Check aggregate counts against raw rows; initial views can legitimately be empty.
- Verify uptime time series after at least two intervals; don't take production down
  to test alerts. Verify email delivery through Monitoring's test/verification UI.
- Rollback: disable the named sink, alert policies and uptime check; revert telemetry
  code if needed. Keep datasets for investigation until explicit deletion approval.
