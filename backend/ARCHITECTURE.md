# Wardrub Backend Architecture

A comprehensive guide to the **Nano Wardrobe** backend - a virtual wardrobe and try-on application powered by Google Cloud AI services.

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Core Concepts](#core-concepts)
5. [API Routes](#api-routes)
6. [Services Layer](#services-layer)
7. [Data Models](#data-models)
8. [Authentication Flow](#authentication-flow)
9. [Background Jobs](#background-jobs)
10. [External Integrations](#external-integrations)
11. [Configuration](#configuration)
12. [Data Flow Diagrams](#data-flow-diagrams)

---

## Overview

Wardrub is a **virtual wardrobe management system** that allows users to:
- Upload photos of their clothing items
- Create a full-body avatar from selfies or full-body photos
- Try on clothes virtually using AI
- Get personalized outfit recommendations based on:
  - Skin tone analysis (seasonal color typing)
  - Body type analysis
  - Weather conditions
  - Occasion type
- View pre-generated "Daily Looks" with rendered try-on images

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.12+) |
| **AI/ML** | Google Gemini (via `google-genai`) for image generation & analysis |
| **Database** | Google Firestore (NoSQL) |
| **Storage** | Google Cloud Storage (GCS) |
| **Authentication** | Firebase Authentication |
| **Background Jobs** | APScheduler |
| **Image Processing** | PIL/Pillow, rembg (background removal) |
| **Weather API** | OpenWeatherMap |

### Key Dependencies
```
fastapi==0.115.0
google-genai>=1.0.0
google-cloud-storage==2.18.0
google-cloud-firestore==2.16.0
google-cloud-aiplatform==1.60.0
rembg==2.0.57
apscheduler==3.10.4
```

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point & lifespan
│   ├── config.py            # Settings & environment variables
│   ├── logging_config.py    # Structured logging setup
│   │
│   ├── middleware/
│   │   └── auth.py          # Auth middleware (attaches user to request)
│   │
│   ├── models/              # Pydantic data models
│   │   ├── garment.py       # GarmentMetadata, colors, visibility
│   │   ├── outfit.py        # OutfitSuggestion, weather info
│   │   ├── user_profile.py  # UserProfile, skin tone, body type
│   │   └── daily_looks.py   # DailyLooks pre-generated outfits
│   │
│   ├── routers/             # API endpoints
│   │   ├── garment.py       # Garment upload, processing, wardrobe
│   │   ├── avatar.py        # Avatar creation (selfie/fullbody)
│   │   ├── tryon.py         # Virtual try-on endpoints
│   │   ├── profile.py       # User profile analysis & settings
│   │   └── outfit.py        # Recommendations & daily looks
│   │
│   ├── services/            # Business logic layer
│   │   ├── auth.py          # Firebase token verification
│   │   ├── firestore.py     # Database operations
│   │   ├── storage.py       # GCS file operations
│   │   ├── vertex_ai.py     # Gemini AI image generation
│   │   ├── background.py    # Background removal (rembg)
│   │   ├── segmentation.py  # Garment segmentation
│   │   ├── color_analysis.py    # Color extraction & harmony
│   │   ├── body_analysis.py     # Body type detection
│   │   ├── recommendation.py    # Outfit recommendation engine
│   │   ├── weather.py           # OpenWeatherMap integration
│   │   ├── product_matcher.py   # Google Vision product search
│   │   └── quality_assessment.py # Image quality scoring
│   │
│   └── jobs/                # Background tasks
│       ├── scheduler.py             # APScheduler setup
│       ├── daily_looks_generator.py # Generate daily outfit images
│       └── backfill_descriptions.py # Backfill missing garment descriptions
│
├── requirements.txt
├── Dockerfile
└── service-account.json     # GCP credentials (gitignored)
```

---

## Core Concepts

### 1. Garment Processing Pipeline

When a user uploads a garment image:

```
User Upload → Quality Assessment → Background Removal → Ghost Mannequin 
     ↓                                                        ↓
Color Analysis ← Segmentation (SAM/rembg) ← Gemini Processing
     ↓
Store Metadata in Firestore + Image in GCS
```

**Ghost Mannequin Effect**: Using Gemini, the garment is rendered as if displayed on an invisible mannequin - giving it a 3D shape for better visualization.

### 2. Avatar Creation

Two modes are supported:

| Mode | Description |
|------|-------------|
| **Upload** | Full-body photo → Processed into neutral-pose avatar wearing simple clothes |
| **Selfie** | Face photo → Gemini generates full-body from face with matching features |

### 3. Virtual Try-On

Combines avatar + garment(s) using Gemini's image generation:
- Single garment try-on
- Multi-garment outfits (up to 4 items)

### 4. Recommendation Engine

Scoring factors:
- **Color Harmony (35%)**: Does garment color complement user's skin tone?
- **Fit Score (25%)**: Does garment fit type suit body type?
- **Weather Score (40%)**: Is it appropriate for current weather?

---

## API Routes

### Garment Router (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process-garment` | Upload front/back images, apply ghost mannequin |
| `POST` | `/process-uploaded-clothes` | AI detects clothes in image, creates mannequins |
| `POST` | `/process-garment-full` | Full pipeline with quality, color, visibility analysis |
| `GET` | `/wardrobe` | List user's garments |
| `DELETE` | `/garment/{id}` | Remove garment |
| `GET` | `/garment/{id}/metadata` | Get analysis data for garment |
| `POST` | `/find-similar-products` | Google Vision product search |
| `POST` | `/garment/{id}/confirm-match` | Extract product details from matched image |

### Avatar Router (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/create-avatar` | Create avatar from photo (upload/selfie mode) |
| `POST` | `/create-avatar-full` | Create avatar + run profile analysis |
| `GET` | `/avatar` | Get current avatar URL |
| `DELETE` | `/avatar` | Remove avatar |

### Try-On Router (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/try-on` | Single garment try-on |
| `POST` | `/try-on-multiple` | Multi-garment outfit try-on |
| `GET` | `/try-on/history` | List saved try-on results |
| `DELETE` | `/look/{id}` | Delete saved look |

### Profile Router (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/profile` | Get user profile |
| `POST` | `/profile/analyze` | Analyze photos for skin tone & body type |
| `PUT` | `/profile` | Update preferences |
| `PUT` | `/profile/location` | Set location for weather |
| `GET` | `/profile/color-recommendations` | Get colors that suit user |
| `GET` | `/profile/fit-recommendations` | Get fit recommendations by body type |
| `POST` | `/migrate-legacy-data` | Migrate old data to user namespace |

### Outfit Router (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/daily-outfit` | Top outfit recommendation for today |
| `POST` | `/recommendations` | Get multiple outfit suggestions |
| `GET` | `/weather` | Current weather + clothing advice |
| `GET` | `/weather/forecast` | Day forecast (morning/noon/evening/night) |
| `GET` | `/daily-looks` | Pre-generated looks for a date |
| `GET` | `/daily-looks/latest` | Most recent generated looks |
| `POST` | `/daily-looks/generate` | Manually trigger look generation |
| `GET` | `/garments/recommended` | Garments sorted by recommendation score |

---

## Services Layer

### `VertexAIService` (vertex_ai.py)
The AI powerhouse - uses **Google Gemini** for:
- Avatar generation from selfies/full-body photos
- Virtual try-on image synthesis
- Ghost mannequin effect creation
- Clothing detection and description

**Key Methods:**
```python
async def process_uploaded_avatar(image_bytes) -> bytes
async def create_avatar_from_selfie(selfie_bytes) -> bytes
async def virtual_try_on(person_image, garment_image, category) -> bytes
async def virtual_try_on_multiple(person_image, garments) -> bytes
async def detect_clothes_in_image(image_bytes) -> List[dict]
async def create_ghost_mannequin_from_description(image_bytes, description, category) -> bytes
```

### `FirestoreService` (firestore.py)
Database layer with **in-memory fallback** when Firestore is unavailable.

**Collections:**
- `user_profiles` - User analysis data, preferences, location
- `garments` - Garment metadata (colors, fit, scores)
- `daily_looks` - Pre-generated outfit looks by date

**Key Features:**
- Automatic sync from GCS storage to metadata store
- Legacy data migration support
- User-scoped queries

### `StorageService` (storage.py)
Google Cloud Storage management with **signed URLs** (24h expiry).

**Path Structure:**
```
users/{user_id}/
├── avatar.png
├── avatar_sources/{type}.png
├── garments/{category}/{id}_front.png
├── garments/{category}/{id}_back.png
├── sources/{garment_id}_{view}.png
└── tryon-results/{id}.png
```

### `RecommendationEngine` (recommendation.py)
Generates outfit combinations by:
1. Scoring each garment (color harmony, fit, weather)
2. Grouping by category (top, bottom, dress, outerwear)
3. Creating combinations (top+bottom, dress, with outerwear if cold)
4. Generating AI reasoning with Gemini

### `ColorAnalysisService` (color_analysis.py)
- Extracts dominant/secondary colors from garments
- Analyzes skin tone → determines seasonal color type (Spring/Summer/Autumn/Winter)
- Calculates harmony scores between garment and user

### `BodyAnalysisService` (body_analysis.py)
- Detects body type from photos (hourglass, pear, apple, rectangle, inverted triangle)
- Provides fit recommendations per garment category

### `WeatherService` (weather.py)
- Fetches current weather via OpenWeatherMap
- Generates clothing recommendations based on temperature
- Day forecast with morning/noon/evening/night periods

---

## Data Models

### GarmentMetadata
```python
class GarmentMetadata:
    garment_id: str
    user_id: str
    category: GarmentCategory  # top, bottom, dress, outerwear
    
    source_images: List[SourceImage]
    ghost_mannequin_url: Optional[str]
    mask_url: Optional[str]
    
    colors: Optional[GarmentColors]       # dominant, secondary, warmth
    description: Optional[GarmentDescription]  # short, detailed, style_tags
    fit_type: Optional[FitType]           # fitted, regular, loose, oversized
    
    season_suitability: List[str]         # spring, summer, autumn, winter
    weather_range: WeatherRange           # min_temp, max_temp
    
    visibility: GarmentVisibility         # score, status
    recommendation_scores: RecommendationScores  # color_harmony, fit, overall
```

### UserProfile
```python
class UserProfile:
    skin_tone: Optional[SkinTone]     # undertone, depth, season
    body_type: Optional[BodyType]     # hourglass, pear, apple, etc.
    body_measurements: Optional[BodyMeasurementsEstimate]
    
    style_preferences: List[str]
    location: Optional[Location]      # lat, lon, city
    source_images: List[str]
    
    analysis_quality: AnalysisQuality  # confidence scores, recommendations
```

### DailyLook
```python
class DailyLook:
    id: str
    outfit_items: List[OutfitItem]    # garment_id, category, image_url
    tryon_image_url: str              # Pre-rendered try-on
    score: float
    reasoning: str
    weather_context: str
    color_harmony_notes: str
```

---

## Authentication Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────>│   Firebase   │────>│   Backend   │
│  (Frontend) │     │     Auth     │     │  (FastAPI)  │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. Sign in        │                    │
      │─────────────────>  │                    │
      │                    │                    │
      │  2. ID Token       │                    │
      │<─────────────────  │                    │
      │                    │                    │
      │  3. API Request with Bearer Token       │
      │─────────────────────────────────────────>
      │                    │                    │
      │                    │  4. Verify Token   │
      │                    │<───────────────────│
      │                    │                    │
      │                    │  5. Decoded Claims │
      │                    │───────────────────>│
      │                    │                    │
      │  6. Response with user-scoped data      │
      │<─────────────────────────────────────────
```

**Token Caching**: Verified tokens are cached for 5 minutes to reduce Firebase SDK calls.

**Middleware Flow:**
1. `AuthMiddleware` extracts Bearer token from `Authorization` header
2. `verify_token()` validates with Firebase (or returns cached result)
3. User info attached to `request.state.user`
4. Route handlers use `Depends(get_current_user)` to require auth

---

## Background Jobs

### APScheduler Setup
Configured in `app/jobs/scheduler.py`, started in `main.py` lifespan.

### Daily Looks Generator
**Schedule:** 6:00 AM UTC (currently disabled for multi-user)

**Process:**
1. Get user profile with location
2. Fetch weather forecast
3. Score all garments for weather/color/fit
4. Generate top 3 outfit combinations
5. Render try-on images via Gemini
6. Store in Firestore as `DailyLooks`

### Description Backfill
Runs on startup - finds garments missing descriptions and generates them via AI.

---

## External Integrations

### Google Gemini (AI)
```python
# Model selection via config
GEMINI_MODEL_TYPE = "flash"  # or "pro"
GEMINI_MODELS = {
    "pro": "gemini-3-pro-image-preview",
    "flash": "gemini-2.5-flash-image",
}
```

Used for:
- Image generation (avatars, try-on, ghost mannequin)
- Image analysis (clothing detection, skin tone, body type)
- Text generation (outfit reasoning)

### Google Cloud Vision (Product Search)
Via `ProductMatcherService`:
- Find visually similar products online
- Extract web entities and best-guess labels
- Match user garments to product listings

### OpenWeatherMap
- Current weather by coordinates
- Hourly forecast for day planning
- Temperature-based clothing recommendations

---

## Configuration

### Environment Variables
```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=service-account.json
GCS_BUCKET=your-bucket-name
VERTEX_AI_LOCATION=us-central1

# Model Selection
GEMINI_MODEL_TYPE=flash  # or "pro"

# Authentication
# (Uses Firebase project from GCP credentials)

# APIs
OPENWEATHER_API_KEY=your-api-key
REPLICATE_API_TOKEN=your-token  # For SAM segmentation

# Server
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=http://localhost:5173

# Recommendations
MIN_VISIBILITY_SCORE=0.5
MAX_OUTFIT_SUGGESTIONS=10
```

### Settings Class (`config.py`)
```python
class Settings:
    GOOGLE_CLOUD_PROJECT: str
    GCS_BUCKET: str
    GEMINI_MODEL: str
    TARGET_IMAGE_SIZE: int = 1024
    ALLOWED_ORIGINS: list[str]
    # ... etc
```

---

## Data Flow Diagrams

### Garment Upload Flow
```
┌──────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────┐
│  User    │───>│  Quality   │───>│  Background │───>│  Gemini  │
│  Upload  │    │  Check     │    │   Removal   │    │  Ghost   │
└──────────┘    └────────────┘    │  (rembg)    │    │ Mannequin│
                                  └─────────────┘    └──────────┘
                                                           │
┌──────────┐    ┌────────────┐    ┌─────────────┐          │
│ Firestore│<───│   Color    │<───│ Segmentation│<─────────┘
│ Metadata │    │  Analysis  │    │   (mask)    │
└──────────┘    └────────────┘    └─────────────┘
      │
      v
┌──────────┐
│   GCS    │
│  Storage │
└──────────┘
```

### Recommendation Flow
```
┌──────────────┐
│ User Request │
│ GET /daily-  │
│    outfit    │
└──────┬───────┘
       │
       v
┌──────────────┐     ┌──────────────┐
│ Get Profile  │────>│ Get Weather  │
│  (Firestore) │     │ (OpenWeather)│
└──────────────┘     └──────────────┘
       │                    │
       v                    v
┌──────────────────────────────────┐
│       Score All Garments         │
│  - Color harmony (35%)           │
│  - Fit score (25%)               │
│  - Weather score (40%)           │
└──────────────┬───────────────────┘
               │
               v
┌──────────────────────────────────┐
│    Generate Outfit Combinations   │
│  - Top + Bottom                   │
│  - Dress                          │
│  - + Outerwear if cold            │
└──────────────┬───────────────────┘
               │
               v
┌──────────────────────────────────┐
│   Gemini: Generate Reasoning      │
│  "This outfit works because..."   │
└──────────────┬───────────────────┘
               │
               v
┌──────────────────────────────────┐
│         Return Response           │
│  - Items with URLs                │
│  - Scores                         │
│  - Weather info                   │
│  - AI reasoning                   │
└──────────────────────────────────┘
```

---

## Running the Backend

### Local Development
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
export GOOGLE_APPLICATION_CREDENTIALS=service-account.json
export GOOGLE_CLOUD_PROJECT=your-project
export GCS_BUCKET=your-bucket
export OPENWEATHER_API_KEY=your-key

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker build -t wardrub-backend .
docker run -p 8000:8000 \
  -v $(pwd)/service-account.json:/app/service-account.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
  wardrub-backend
```

### API Documentation
Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Summary

The Wardrub backend is a **FastAPI application** that orchestrates:

1. **Image Processing** - Background removal, ghost mannequin effect, quality assessment
2. **AI Analysis** - Skin tone, body type, color harmony, clothing detection
3. **Personalized Recommendations** - Weather-aware, profile-matched outfit suggestions
4. **Virtual Try-On** - AI-generated images of user wearing clothes
5. **Data Management** - Multi-user storage with GCS + Firestore

All protected by **Firebase Authentication** and powered by **Google Gemini** for AI capabilities.
