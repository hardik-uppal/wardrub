"""Firebase Authentication service for verifying user tokens."""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
import hashlib

import firebase_admin
from firebase_admin import auth, credentials

from app.config import get_settings
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger("auth")

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)

# Firebase Admin initialization flag
_firebase_initialized = False

# Token verification cache (token_hash -> (decoded_token, expiry_time))
# Cache tokens for 5 minutes to reduce Firebase SDK calls
_token_cache: Dict[str, tuple] = {}
_TOKEN_CACHE_TTL = 300  # 5 minutes in seconds
_MAX_CACHE_SIZE = 1000  # Prevent unbounded growth


def _get_token_hash(token: str) -> str:
    """Get a hash of the token for cache key (don't store full token)."""
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def _cleanup_cache():
    """Remove expired entries from cache."""
    global _token_cache
    now = time.time()
    _token_cache = {k: v for k, v in _token_cache.items() if v[1] > now}


def initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK using the service account credentials.
    
    Returns:
        True if initialization successful or already initialized
    """
    global _firebase_initialized
    
    if _firebase_initialized:
        return True
    
    try:
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app(cred, {
                'projectId': settings.GOOGLE_CLOUD_PROJECT
            })
        else:
            # Use default credentials (for Cloud Run)
            firebase_admin.initialize_app(options={
                'projectId': settings.GOOGLE_CLOUD_PROJECT
            })
        
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully")
        return True
        
    except ValueError as e:
        # App already initialized
        if "already exists" in str(e):
            _firebase_initialized = True
            return True
        logger.error(f"Failed to initialize Firebase Admin: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin: {e}")
        return False


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token and return the decoded claims.
    Uses caching to reduce Firebase SDK calls.
    
    Args:
        token: Firebase ID token from client
    
    Returns:
        Decoded token claims including uid, email, etc.
        None if verification fails
    """
    if not _firebase_initialized:
        initialize_firebase()
    
    # Check cache first
    token_hash = _get_token_hash(token)
    now = time.time()
    
    if token_hash in _token_cache:
        cached_token, expiry = _token_cache[token_hash]
        if expiry > now:
            # Cache hit - return cached result
            return cached_token
        else:
            # Expired - remove from cache
            del _token_cache[token_hash]
    
    # Cache miss - verify with Firebase
    try:
        decoded_token = auth.verify_id_token(token)
        
        # Cache the result (cleanup old entries periodically)
        if len(_token_cache) > _MAX_CACHE_SIZE:
            _cleanup_cache()
        
        _token_cache[token_hash] = (decoded_token, now + _TOKEN_CACHE_TTL)
        return decoded_token
        
    except auth.ExpiredIdTokenError:
        logger.warning("Token expired")
        return None
    except auth.RevokedIdTokenError:
        logger.warning("Token revoked")
        return None
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current authenticated user.
    
    Args:
        credentials: Bearer token from Authorization header
    
    Returns:
        User info dict with uid, email, name, etc.
    
    Raises:
        HTTPException 401 if not authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user_info = verify_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to optionally get the current user.
    Returns None if not authenticated instead of raising an exception.
    
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    return verify_token(token)


def get_user_id(user: Dict[str, Any]) -> str:
    """
    Extract user ID from decoded token.
    
    Args:
        user: Decoded token from verify_token or get_current_user
    
    Returns:
        Firebase user UID
    """
    return user.get("uid", "")

