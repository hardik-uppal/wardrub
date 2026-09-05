#!/usr/bin/env bash
# Trigger the secured GitHub Actions production deployment.
#
# Production credentials live in GitHub Actions secrets and are passed directly
# to Cloud Run by .github/workflows/deploy.yml. Do not add credentials here.

set -euo pipefail

REPOSITORY="${WARDRUB_REPOSITORY:-hardik-uppal/wardrub}"
REF="${WARDRUB_DEPLOY_REF:-main}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Authenticate GitHub CLI before deploying: gh auth login" >&2
  exit 1
fi

echo "Triggering the secured Wardrub deployment for ${REF}"
gh workflow run "Deploy Wardrub" --repo "$REPOSITORY" --ref "$REF"
echo "Deployment requested. Monitor it with:"
echo "gh run watch --repo ${REPOSITORY}"
