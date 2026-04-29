"""Configuration settings for the Nano Wardrobe backend."""

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


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
    "flash": "gemini-2.5-flash-image",
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
    
    # Replicate API (for SAM serverless)
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
    
    # OpenWeatherMap
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    
    # Recommendation Engine
    MIN_VISIBILITY_SCORE: float = float(os.getenv("MIN_VISIBILITY_SCORE", "0.5"))
    MAX_OUTFIT_SUGGESTIONS: int = int(os.getenv("MAX_OUTFIT_SUGGESTIONS", "10"))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

