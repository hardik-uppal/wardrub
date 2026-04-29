"""FastAPI application entry point for Nano Wardrobe backend."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

from app.config import get_settings
from app.routers import garment, avatar, tryon, profile, outfit
from app.logging_config import setup_logging, get_logger
from app.middleware.auth import AuthMiddleware
from app.services.auth import initialize_firebase

settings = get_settings()

# Initialize logging
setup_logging(level="DEBUG")
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler for startup and shutdown events.
    
    On startup:
    - Initialize Firebase Authentication
    - Run description backfill for garments without descriptions
    - Start the APScheduler for daily jobs
    
    On shutdown:
    - Stop the scheduler gracefully
    """
    logger.info("🚀 Starting Nano Wardrobe API...")
    
    # Initialize Firebase Admin SDK
    logger.info("🔐 Initializing Firebase Authentication...")
    if initialize_firebase():
        logger.info("✅ Firebase initialized")
    else:
        logger.warning("⚠️ Firebase initialization failed - auth will not work")
    
    # Import here to avoid circular imports
    from app.jobs.scheduler import setup_scheduler, start_scheduler, stop_scheduler
    from app.jobs.backfill_descriptions import run_backfill_if_needed
    
    # Start background description backfill
    logger.info("📋 Starting description backfill check...")
    asyncio.create_task(run_backfill_if_needed())
    
    # Setup and start scheduler
    logger.info("⏰ Setting up scheduler...")
    setup_scheduler(daily_looks_hour=6, daily_looks_minute=0)
    start_scheduler()
    
    logger.info("✅ Startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    stop_scheduler()
    logger.info("👋 Shutdown complete")


app = FastAPI(
    title="Nano Wardrobe API",
    description="Virtual wardrobe and try-on backend powered by Vertex AI",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for mobile web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # Log request
    logger.info(f"📨 [{request_id}] {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(f"📬 [{request_id}] {response.status_code} ({duration:.2f}s)")
    
    return response


# Include routers
app.include_router(garment.router, prefix="/api", tags=["Garment"])
app.include_router(avatar.router, prefix="/api", tags=["Avatar"])
app.include_router(tryon.router, prefix="/api", tags=["Try-On"])
app.include_router(profile.router, prefix="/api", tags=["Profile"])
app.include_router(outfit.router, prefix="/api", tags=["Outfit"])


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {"status": "healthy", "service": "Nano Wardrobe API"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}

