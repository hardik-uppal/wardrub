# Wardrub Project — Agent Memory

## Owner & Accounts

- **Personal Name:** Hardik Uppal
- **Personal Email:** hardikuppal.hu@gmail.com
- **GitHub:** github.com/hardik-uppal (personal account — ALL project repos live here)
- **Work Email:** hardik.u@aftershoot.com (Aftershoot) — **NOT used for this project**

> ⚠️ Everything in this project belongs to the personal account (`hardikuppal.hu@gmail.com`).
> Never use the Aftershoot GCP project (`aftershoot-stage`, `aftershoot-co`) or the Aftershoot GitHub org for any Wardrub deployments.

## GCP / Firebase

- **GCP Project ID:** `gen-lang-client-0842206246` (personal project, name: "clothing-manager")
- **GCP Project Number:** `1028744939274`
- **Service Account:** `drub-user@gen-lang-client-0842206246.iam.gserviceaccount.com`
- **Service Account Key:** `backend/service-account.json`
- **Firebase Auth Domain:** `gen-lang-client-0842206246.firebaseapp.com`
- **Firebase Storage Bucket:** `gen-lang-client-0842206246.firebasestorage.app`
- **Firebase App ID:** `1:1028744939274:web:832d2b8d48fee7ffb19cf3`
- **Firebase Messaging Sender ID:** `1028744939274`
- **GCS Assets Bucket:** `wardrub-assets-1`
- **Cloud Run Region:** `us-central1`
- **Cloud Run Service Name:** `wardrub-api`

## Deployment Targets

- **Frontend:** GitHub Pages → `github.com/hardik-uppal/wardrub` (`gh-pages` branch)
- **Custom Domain:** `https://wardrub.hardk.space` (root subdomain deployment)
- **Backend:** Google Cloud Run (`gen-lang-client-0842206246`, `us-central1`)
- **Image Registry:** `us-central1-docker.pkg.dev/gen-lang-client-0842206246/wardrub/wardrub-api`

## IAM Roles Configured

The service account `drub-user@gen-lang-client-0842206246.iam.gserviceaccount.com` has the following roles:
- `roles/run.admin`
- `roles/artifactregistry.writer`
- `roles/storage.objectAdmin`
- `roles/iam.serviceAccountUser`

Deployments using `./deploy.sh` succeed out of the box now.
