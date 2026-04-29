"""Authentication middleware for request processing."""

from typing import Callable, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.auth import verify_token, initialize_firebase
from app.logging_config import get_logger

logger = get_logger("auth_middleware")

# Paths that don't require authentication
PUBLIC_PATHS = [
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
]

# Path prefixes that are public (for docs assets etc.)
PUBLIC_PREFIXES = [
    "/docs",
    "/redoc",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches user info to request state.
    
    This middleware:
    - Initializes Firebase on first request
    - Extracts Bearer token from Authorization header
    - Verifies token and attaches user to request.state.user
    - Allows public endpoints without authentication
    
    Note: This doesn't block requests - that's done by the get_current_user dependency.
    This middleware just makes user info available to all handlers.
    """
    
    def __init__(self, app: Callable, public_paths: List[str] = None):
        super().__init__(app)
        self.public_paths = public_paths or PUBLIC_PATHS
        self._firebase_initialized = False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ensure Firebase is initialized
        if not self._firebase_initialized:
            initialize_firebase()
            self._firebase_initialized = True
        
        # Initialize user as None
        request.state.user = None
        
        # Check for authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            user_info = verify_token(token)
            if user_info:
                request.state.user = user_info
                logger.debug(f"Authenticated user: {user_info.get('email', user_info.get('uid'))}")
        
        # Continue to the next middleware/route handler
        response = await call_next(request)
        return response



