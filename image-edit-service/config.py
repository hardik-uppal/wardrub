"""Configuration for the Qwen-Image-Edit-2511 Service."""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Service settings from environment variables."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Model - Pre-quantized 4-bit version of Qwen-Image-Edit-2511
    MODEL_ID: str = "toandev/Qwen-Image-Edit-2511-4bit"
    
    # Lightning LoRA for faster inference (4 steps instead of 40)
    USE_LIGHTNING_LORA: bool = True
    LIGHTNING_LORA_REPO: str = "lightx2v/Qwen-Image-Edit-2511-Lightning"
    LIGHTNING_LORA_WEIGHT: str = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
    
    # Generation settings for Qwen-Image-Edit-2511
    # With Lightning LoRA: 4 steps, without: 40 steps
    NUM_INFERENCE_STEPS: int = 4
    GUIDANCE_SCALE: float = 1.0
    TRUE_CFG_SCALE: float = 4.0
    
    # Memory optimization
    ENABLE_CPU_OFFLOAD: bool = True
    
    # Output - Portrait orientation for mobile
    OUTPUT_WIDTH: int = 768
    OUTPUT_HEIGHT: int = 1024
    
    # CORS - add your backend URL
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    
    # Cache directory for model weights
    CACHE_DIR: str = os.path.expanduser("~/.cache/huggingface")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
