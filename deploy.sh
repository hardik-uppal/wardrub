#!/bin/bash
# =========================================================================
# ⚠️ DEPRECATED ⚠️
# Wardrub now uses an automated CI/CD pipeline via GitHub Actions.
# Whenever you push to the 'main' branch, it deploys automatically!
# 
# This script should ONLY be used for local manual emergency deployments.
# =========================================================================
# Back-end: Google Cloud Run
# Front-end: GitHub Pages (hardk.space/wardrub)

set -e

# Config
PROJECT_ID="gen-lang-client-0842206246"
SERVICE_NAME="wardrub-api"
REGION="us-central1"
AR_REGION="us-central1"
AR_REPO="wardrub"
IMAGE_TAG="${AR_REGION}-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME"
ALLOWED_ORIGIN="https://wardrub.hardk.space,https://hardk.space,https://hardik-uppal.github.io"

echo "============================================="
echo "🚀 STARTING WARDRUB PRODUCTION DEPLOYMENT"
echo "============================================="

# 1. Ensure gcloud is configured
echo "🔧 Configuring gcloud project..."
gcloud auth activate-service-account --key-file=backend/service-account.json
gcloud config set project "$PROJECT_ID"

# 2. Ensure Artifact Registry repo exists
echo "🗂️  Ensuring Artifact Registry repo exists..."
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker \
  --location="$AR_REGION" \
  --project="$PROJECT_ID" \
  --quiet 2>/dev/null || echo "  (repo already exists, continuing)"

# 3. Build and push backend image
echo "📦 Building backend image locally with Docker..."
gcloud auth configure-docker "${AR_REGION}-docker.pkg.dev" --quiet
docker build -t "$IMAGE_TAG" backend/
echo "📤 Pushing image to Artifact Registry..."
docker push "$IMAGE_TAG"

echo "🌐 Deploying backend to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_TAG" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --timeout=300 \
  --cpu=2 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars="^##^GOOGLE_CLOUD_PROJECT=$PROJECT_ID##GCS_BUCKET=wardrub-assets-1##ALLOWED_ORIGINS=$ALLOWED_ORIGIN##VERTEX_AI_LOCATION=us-central1##GEMINI_API_KEY=AIzaSyDPD1rwAPORD54bOW6u068WbzBoj7hhjps##GEMINI_MODEL_TYPE=pro##GEMINI_TEXT_MODEL=gemini-2.0-flash-lite##OPENWEATHER_API_KEY=b6269b61808f6937854e57cf13df6967##REPLICATE_API_TOKEN=r8_XFI00pbliTGwzmGcT4XRVGxvv9QYDDS4IXrb9"

# 3. Retrieve Cloud Run service URL
echo "🔍 Retrieving Cloud Run URL..."
BACKEND_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)')
echo "✅ Backend URL: $BACKEND_URL"

# 4. Generate frontend/.env.production
echo "📝 Writing frontend/.env.production..."
cat << EOF > frontend/.env.production
# Production API URL
VITE_API_URL=$BACKEND_URL

# Firebase Configuration
VITE_FIREBASE_API_KEY=AIzaSyAuLmq_YQTxPJTdRCd3YhbQtVjCgdTTD1k
VITE_FIREBASE_AUTH_DOMAIN=gen-lang-client-0842206246.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=gen-lang-client-0842206246
VITE_FIREBASE_STORAGE_BUCKET=gen-lang-client-0842206246.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=1028744939274
VITE_FIREBASE_APP_ID=1:1028744939274:web:832d2b8d48fee7ffb19cf3
EOF

# 5. Build frontend
echo "🏗️ Building frontend React application..."
cd frontend
npm install
npm run build
cd ..

# 6. Deploy to GitHub Pages
echo "✈️ Publishing frontend to GitHub Pages..."
cd frontend/dist
echo "wardrub.hardk.space" > CNAME
rm -rf .git
git init
git checkout -B gh-pages
git add -A
git commit -m "Production release to hardk.space/wardrub"
git remote add origin git@github.com:hardik-uppal/wardrub.git
git push -f origin gh-pages
cd ../..

echo "============================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "Frontend: https://hardk.space/wardrub/"
echo "Backend:  $BACKEND_URL"
echo "============================================="
