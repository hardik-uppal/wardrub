# Nano Wardrobe - Virtual Try-On POC

A mobile-first Progressive Web App for digitizing your wardrobe and virtually trying on clothes using AI.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React PWA)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Camera    │  │  Wardrobe   │  │    Dressing Room        │ │
│  │   Capture   │  │    Grid     │  │    (Try-On Screen)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ /process-   │  │  /create-   │  │       /try-on           │ │
│  │   garment   │  │    avatar   │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                   │                     │
          ▼                   ▼                     ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
│    rembg     │    │   Imagen 3      │    │  Virtual Try-On  │
│  (local AI)  │    │  (Vertex AI)    │    │   (Vertex AI)    │
└──────────────┘    └─────────────────┘    └──────────────────┘
```

## Tech Stack

- **Frontend**: React + Vite + Tailwind CSS + Lucide Icons
- **Backend**: Python FastAPI
- **AI Services**: 
  - `rembg` for background removal
  - Google Vertex AI Imagen 3 for avatar generation
  - Google Vertex AI Virtual Try-On for outfit synthesis
- **Storage**: Google Cloud Storage

## Prerequisites

1. **Node.js** 18+ and npm
2. **Python** 3.10+
3. **Google Cloud Project** with:
   - Vertex AI API enabled
   - Cloud Storage API enabled
   - Service account with `Vertex AI User` and `Storage Object Admin` roles

## Getting Started

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your GCP project details

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Google Cloud Configuration

1. Create a GCP project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable APIs:
   - Vertex AI API
   - Cloud Storage API
3. Create a Service Account:
   - Go to IAM & Admin > Service Accounts
   - Create new service account
   - Add roles: `Vertex AI User`, `Storage Object Admin`
   - Create and download JSON key
4. Create a Cloud Storage bucket:
   - Name it `wardrub-assets-{your-project-id}`
5. Place the service account JSON in `backend/service-account.json`
6. Update `backend/.env` with your project ID and bucket name

## Environment Variables

### Backend (.env)

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
GCS_BUCKET=wardrub-assets-your-project-id
ALLOWED_ORIGINS=http://localhost:5173
VERTEX_AI_LOCATION=us-central1
```

### Frontend (.env.development)

```env
VITE_API_URL=http://localhost:8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/process-garment` | POST | Upload and clean garment image |
| `/api/wardrobe` | GET | List all garments |
| `/api/garment/{id}` | DELETE | Delete a garment |
| `/api/create-avatar` | POST | Generate full-body avatar |
| `/api/avatar` | GET | Get current avatar |
| `/api/try-on` | POST | Generate virtual try-on |

## Usage

1. **Create Avatar**: Upload 1-3 selfies to generate your virtual avatar
2. **Add Clothes**: Take photos of garments; AI removes backgrounds automatically
3. **Try On**: Select items from your digital wardrobe to see them on your avatar

## Development

```bash
# Run both frontend and backend in development mode

# Terminal 1 - Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## Deployment

### Backend (Cloud Run)

```bash
cd backend
gcloud builds submit --tag gcr.io/YOUR_PROJECT/wardrub-api
gcloud run deploy wardrub-api --image gcr.io/YOUR_PROJECT/wardrub-api --platform managed
```

### Frontend (Firebase Hosting / Vercel / Netlify)

```bash
cd frontend
npm run build
# Deploy dist/ folder to your preferred hosting
```

## License

MIT





