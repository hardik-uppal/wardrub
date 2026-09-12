#!/usr/bin/env bash
# Dedicated metadata-only collector, every six hours. No photo-read permission.
set -euo pipefail
export CLOUDSDK_CORE_ACCOUNT=hardikuppal.hu@gmail.com
export CLOUDSDK_CORE_PROJECT=gen-lang-client-0842206246
P="$CLOUDSDK_CORE_PROJECT"
REGION=us-central1
SA="wardrub-analytics@$P.iam.gserviceaccount.com"
SCHEDULER="wardrub-analytics-scheduler@$P.iam.gserviceaccount.com"
DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" != --apply ]]; then
  echo 'Plan: enable Build/Scheduler APIs; create metadata-reader collector SA, private six-hour Cloud Run Job and scheduler invoker SA. Billable usage is possible. Pass --apply to provision.'
  exit 0
fi
gcloud services enable cloudbuild.googleapis.com cloudscheduler.googleapis.com --quiet
for name in wardrub-analytics wardrub-analytics-scheduler; do
  if ! gcloud iam service-accounts describe "$name@$P.iam.gserviceaccount.com" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$name" --display-name="$name"
  fi
done
PERMS=datastore.entities.get,datastore.entities.list,firebaseauth.users.get,storage.objects.list,bigquery.jobs.create
if gcloud iam roles describe wardrubAnalyticsCollector --project="$P" >/dev/null 2>&1; then
  gcloud iam roles update wardrubAnalyticsCollector --project="$P" --permissions="$PERMS" --quiet
else
  gcloud iam roles create wardrubAnalyticsCollector --project="$P" --title='Wardrub metadata inventory' --permissions="$PERMS" --stage=GA
fi
gcloud projects add-iam-policy-binding "$P" --member="serviceAccount:$SA" --role="projects/$P/roles/wardrubAnalyticsCollector" --condition=None --quiet >/dev/null
# Only this analytics dataset, not project-wide data editor.
python3 - "$SA" "$DIR" <<'PY'
import sys
sys.path.insert(0,sys.argv[2])
from user_snapshot import api,BASE
url=BASE+'/datasets/wardrub_events'
d=api('GET',url)
access=d.get('access',[])
grant={'role':'WRITER','userByEmail':sys.argv[1]}
if grant not in access:api('PATCH',url,{'access':access+[grant]})
PY
IMAGE="$REGION-docker.pkg.dev/$P/wardrub/analytics-snapshot:$(date -u +%Y%m%d%H%M%S)"
gcloud builds submit "$DIR" --tag="$IMAGE" --quiet
gcloud run jobs deploy wardrub-analytics-snapshot --image="$IMAGE" --region="$REGION" \
  --service-account="$SA" --memory=512Mi --cpu=1 --tasks=1 --max-retries=1 --task-timeout=300s --quiet
gcloud run jobs add-iam-policy-binding wardrub-analytics-snapshot --region="$REGION" \
  --member="serviceAccount:$SCHEDULER" --role=roles/run.invoker --quiet >/dev/null
URI="https://run.googleapis.com/v2/projects/$P/locations/$REGION/jobs/wardrub-analytics-snapshot:run"
ACTION=create
if gcloud scheduler jobs describe wardrub-analytics-snapshot --location="$REGION" >/dev/null 2>&1; then ACTION=update; fi
gcloud scheduler jobs "$ACTION" http wardrub-analytics-snapshot --location="$REGION" \
  --schedule='0 */6 * * *' --time-zone=UTC --uri="$URI" --http-method=POST \
  --oauth-service-account-email="$SCHEDULER" --headers=Content-Type=application/json --message-body='{}' --quiet
gcloud run jobs execute wardrub-analytics-snapshot --region="$REGION" --wait --quiet
