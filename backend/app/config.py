"""Configuration settings for the Nano Wardrobe backend."""

import os
import json
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv(override=True)

# Print masked GEMINI_API_KEY for debugging key loading
_key = os.getenv("GEMINI_API_KEY")
if _key:
    print(f"🔑 Loaded GEMINI_API_KEY: {_key[:6]}...{_key[-6:] if len(_key) > 12 else ''}")
else:
    print("🔑 Loaded GEMINI_API_KEY: None")


# Setup service account credentials file from env string if running on Cloud Run
import base64

gcp_key_b64 = os.getenv("GCP_SERVICE_ACCOUNT_KEY_B64")
gcp_key = os.getenv("GCP_SERVICE_ACCOUNT_KEY")

if gcp_key_b64:
    try:
        gcp_key = base64.b64decode(gcp_key_b64).decode('utf-8')
    except Exception as e:
        print(f"Error decoding base64 service account key: {e}")

if gcp_key:
    temp_path = "/tmp/service-account.json"
    try:
        json_data = json.loads(gcp_key)
        with open(temp_path, "w") as f:
            json.dump(json_data, f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path
    except Exception as e:
        print(f"Error writing service account key to {temp_path}: {e}")



# =============================================================================
# GEMINI MODEL CONFIGURATION
# =============================================================================
# Change this to switch between models:
#   "pro"   -> gemini-3-pro-image-preview (best quality, slower)
#   "flash" -> gemini-2.0-flash-exp (faster, good quality)
# =============================================================================
GEMINI_MODEL_TYPE = os.getenv("GEMINI_MODEL_TYPE", "flash")  # "pro" or "flash"

# Model mappings
GEMINI_MODELS = {
    "pro": "gemini-3-pro-image-preview",
    "flash": "gemini-3.1-flash-image-preview",
}


def get_gemini_model() -> str:
    """Get the configured Gemini model name."""
    return GEMINI_MODELS.get(GEMINI_MODEL_TYPE, GEMINI_MODELS["flash"])


class Settings:
    """Application settings loaded from environment variables."""
    
    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    GCS_BUCKET: str = os.getenv("GCS_BUCKET", "")
    
    # CORS
    ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Image Processing
    TARGET_IMAGE_SIZE: int = 1024  # Optimal size for Vertex AI
    
    # Vertex AI
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    
    # Gemini
    GEMINI_MODEL: str = get_gemini_model()
    GEMINI_TEXT_MODEL: str = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash-lite")

    
    # Fal.ai API (for SAM serverless)
    FAL_KEY: str = os.getenv("FAL_KEY", "")
    
    # OpenWeatherMap
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    
    # Recommendation Engine
    MIN_VISIBILITY_SCORE: float = float(os.getenv("MIN_VISIBILITY_SCORE", "0.5"))
    MAX_OUTFIT_SUGGESTIONS: int = int(os.getenv("MAX_OUTFIT_SUGGESTIONS", "10"))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

