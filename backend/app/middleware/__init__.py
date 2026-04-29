"""Middleware package for the Wardrub API."""

from app.middleware.auth import AuthMiddleware

__all__ = ["AuthMiddleware"]



