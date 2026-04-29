"""Google Cloud Storage service for image storage and retrieval."""

import uuid
import json
from datetime import timedelta
from typing import Optional, List
from io import BytesIO

from google.cloud import storage
from google.oauth2 import service_account

from app.config import get_settings
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger("storage")


class StorageService:
    """Service for managing images in Google Cloud Storage."""
    
    # Legacy paths (before multi-user support)
    LEGACY_GARMENTS_PREFIX = "garments/"
    LEGACY_AVATAR_PATH = "avatars/current.png"
    LEGACY_TRYON_PREFIX = "tryon-results/"
    
    def __init__(self):
        """Initialize the GCS client."""
        self._client = None
        self._bucket = None
    
    @property
    def client(self) -> storage.Client:
        """Lazy initialization of GCS client."""
        if self._client is None:
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                credentials = service_account.Credentials.from_service_account_file(
                    settings.GOOGLE_APPLICATION_CREDENTIALS
                )
                self._client = storage.Client(
                    project=settings.GOOGLE_CLOUD_PROJECT,
                    credentials=credentials
                )
            else:
                # Use default credentials (for Cloud Run)
                self._client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        return self._client
    
    @property
    def bucket(self) -> storage.Bucket:
        """Get the configured GCS bucket."""
        if self._bucket is None:
            self._bucket = self.client.bucket(settings.GCS_BUCKET)
        return self._bucket
    
    def _generate_signed_url(self, blob_name: str, expiration_hours: int = 24) -> str:
        """Generate a signed URL for accessing a blob."""
        blob = self.bucket.blob(blob_name)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET"
        )
        return url
    
    def _user_garment_path(self, user_id: str, category: str, garment_id: str) -> str:
        """Generate the storage path for a user's garment."""
        return f"users/{user_id}/garments/{category}/{garment_id}.png"
    
    def _user_avatar_path(self, user_id: str) -> str:
        """Generate the storage path for a user's avatar."""
        return f"users/{user_id}/avatar.png"
    
    def _user_tryon_path(self, user_id: str, result_id: str) -> str:
        """Generate the storage path for a user's try-on result."""
        return f"users/{user_id}/tryon-results/{result_id}.png"
    
    async def upload_garment(
        self, 
        image_bytes: bytes, 
        garment_id: str, 
        category: str,
        user_id: str
    ) -> str:
        """
        Upload a processed garment image to GCS.
        
        Args:
            image_bytes: PNG image bytes with transparent background
            garment_id: Unique identifier for the garment
            category: Garment category (top, bottom, dress, outerwear)
            user_id: Owner user ID
        
        Returns:
            Signed URL to access the image
        """
        blob_name = self._user_garment_path(user_id, category, garment_id)
        blob = self.bucket.blob(blob_name)
        
        # Set metadata
        blob.metadata = {
            "category": category,
            "garment_id": garment_id,
            "user_id": user_id
        }
        
        # Upload with content type
        blob.upload_from_string(image_bytes, content_type="image/png")
        
        return self._generate_signed_url(blob_name)
    
    async def upload_avatar(self, image_bytes: bytes, user_id: str) -> str:
        """
        Upload a generated avatar image to GCS.
        
        Args:
            image_bytes: Avatar image bytes
            user_id: Owner user ID
        
        Returns:
            Signed URL to access the avatar
        """
        blob_name = self._user_avatar_path(user_id)
        blob = self.bucket.blob(blob_name)
        
        blob.metadata = {"user_id": user_id}
        blob.upload_from_string(image_bytes, content_type="image/png")
        
        return self._generate_signed_url(blob_name)
    
    async def upload_tryon_result(self, image_bytes: bytes, user_id: str) -> str:
        """
        Upload a try-on result image to GCS.
        
        Args:
            image_bytes: Try-on result image bytes
            user_id: Owner user ID
        
        Returns:
            Signed URL to access the result
        """
        result_id = str(uuid.uuid4())
        blob_name = self._user_tryon_path(user_id, result_id)
        blob = self.bucket.blob(blob_name)
        
        blob.metadata = {"user_id": user_id, "result_id": result_id}
        blob.upload_from_string(image_bytes, content_type="image/png")
        
        return self._generate_signed_url(blob_name)
    
    async def upload_source_image(
        self, 
        image_bytes: bytes, 
        user_id: str,
        garment_id: str,
        view: str = "front",
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload a source image (original user upload) to GCS.
        
        Args:
            image_bytes: Original image bytes
            user_id: Owner user ID
            garment_id: Associated garment ID
            view: View type (front, back, detail)
            content_type: Image MIME type
        
        Returns:
            Signed URL to access the source image
        """
        blob_name = f"users/{user_id}/sources/{garment_id}_{view}.png"
        blob = self.bucket.blob(blob_name)
        
        blob.metadata = {
            "user_id": user_id,
            "garment_id": garment_id,
            "view": view,
            "type": "source"
        }
        blob.upload_from_string(image_bytes, content_type=content_type)
        
        return self._generate_signed_url(blob_name)
    
    async def upload_avatar_source(
        self, 
        image_bytes: bytes, 
        user_id: str,
        source_type: str = "original",
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload the original source image used to create an avatar.
        
        Args:
            image_bytes: Original image bytes
            user_id: Owner user ID
            source_type: Source type (original, selfie, etc.)
            content_type: Image MIME type
        
        Returns:
            Signed URL to access the source image
        """
        blob_name = f"users/{user_id}/avatar_sources/{source_type}.png"
        blob = self.bucket.blob(blob_name)
        
        blob.metadata = {
            "user_id": user_id,
            "source_type": source_type,
            "type": "avatar_source"
        }
        blob.upload_from_string(image_bytes, content_type=content_type)
        
        return self._generate_signed_url(blob_name)
    
    async def get_avatar(self, user_id: str) -> Optional[str]:
        """
        Get a user's avatar URL.
        
        Args:
            user_id: User ID
        
        Returns:
            Signed URL or None if no avatar exists
        """
        blob_name = self._user_avatar_path(user_id)
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            return self._generate_signed_url(blob_name)
        return None
    
    async def delete_avatar(self, user_id: str) -> None:
        """
        Delete a user's avatar.
        
        Args:
            user_id: User ID
        """
        blob_name = self._user_avatar_path(user_id)
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
    
    async def list_garments(self, user_id: str, category: Optional[str] = None) -> List[dict]:
        """
        List all garments in a user's wardrobe, grouped by garment ID.
        Front and back images are combined under the same garment.
        
        Args:
            user_id: User ID
            category: Optional filter by category
        
        Returns:
            List of garment objects with id, urls (front/back), and category
        """
        if category:
            prefix = f"users/{user_id}/garments/{category}/"
        else:
            prefix = f"users/{user_id}/garments/"
        
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        
        # Group by base garment ID
        garment_map = {}
        
        for blob in blobs:
            if blob.name.endswith(".png"):
                # Extract category and id from path
                # Path: users/{user_id}/garments/{category}/{garment_id}.png
                parts = blob.name.split("/")
                if len(parts) >= 5:
                    cat = parts[3]
                    full_id = parts[4].replace(".png", "")
                    
                    # Parse front/back suffix
                    if full_id.endswith("_front"):
                        base_id = full_id[:-6]  # Remove _front
                        view = "front"
                    elif full_id.endswith("_back"):
                        base_id = full_id[:-5]  # Remove _back
                        view = "back"
                    else:
                        # Legacy format without suffix
                        base_id = full_id
                        view = "front"
                    
                    # Initialize garment if not seen
                    if base_id not in garment_map:
                        garment_map[base_id] = {
                            "id": base_id,
                            "category": cat,
                            "front_url": None,
                            "back_url": None,
                            "url": None  # Primary URL for backward compatibility
                        }
                    
                    # Set the appropriate URL
                    url = self._generate_signed_url(blob.name)
                    if view == "front":
                        garment_map[base_id]["front_url"] = url
                        garment_map[base_id]["url"] = url  # Primary URL is front
                    else:
                        garment_map[base_id]["back_url"] = url
        
        return list(garment_map.values())
    
    async def list_tryon_results(self, user_id: str, limit: int = 50) -> List[dict]:
        """
        List recent try-on results (looks) for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of results to return
        
        Returns:
            List of result objects with id and url
        """
        prefix = f"users/{user_id}/tryon-results/"
        blobs = self.client.list_blobs(
            self.bucket, 
            prefix=prefix,
            max_results=limit
        )
        
        results = []
        for blob in blobs:
            if blob.name.endswith(".png"):
                result_id = blob.name.split("/")[-1].replace(".png", "")
                results.append({
                    "id": result_id,
                    "url": self._generate_signed_url(blob.name)
                })
        
        return results
    
    async def delete_look(self, look_id: str, user_id: str) -> None:
        """
        Delete a saved look (try-on result).
        
        Args:
            look_id: The look ID to delete
            user_id: User ID
        """
        blob_name = self._user_tryon_path(user_id, look_id)
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
        else:
            raise ValueError(f"Look {look_id} not found")
    
    async def download_image(self, url: str) -> bytes:
        """
        Download an image from a URL (handles both signed URLs and gs:// paths).
        
        Args:
            url: Image URL or gs:// path
        
        Returns:
            Image bytes
        """
        if url.startswith("gs://"):
            # Parse gs:// URL
            path = url.replace(f"gs://{settings.GCS_BUCKET}/", "")
            blob = self.bucket.blob(path)
            return blob.download_as_bytes()
        else:
            # For signed URLs, extract blob name and download
            # This handles internal storage URLs
            import re
            match = re.search(rf"{settings.GCS_BUCKET}/([^?]+)", url)
            if match:
                blob_name = match.group(1)
                blob = self.bucket.blob(blob_name)
                return blob.download_as_bytes()
            
            # External URL - use requests
            import urllib.request
            with urllib.request.urlopen(url) as response:
                return response.read()
    
    async def delete_garment(self, garment_id: str, user_id: str) -> None:
        """
        Delete a garment from storage (both front and back images).
        
        Args:
            garment_id: The garment ID to delete
            user_id: User ID
        """
        deleted = False
        
        # Search across all categories and delete all variants
        for category in ["top", "bottom", "dress", "outerwear"]:
            # Try front image
            front_blob_name = self._user_garment_path(user_id, category, f"{garment_id}_front")
            front_blob = self.bucket.blob(front_blob_name)
            if front_blob.exists():
                front_blob.delete()
                deleted = True
            
            # Try back image
            back_blob_name = self._user_garment_path(user_id, category, f"{garment_id}_back")
            back_blob = self.bucket.blob(back_blob_name)
            if back_blob.exists():
                back_blob.delete()
                deleted = True
            
            # Try legacy format (no suffix)
            legacy_blob_name = self._user_garment_path(user_id, category, garment_id)
            legacy_blob = self.bucket.blob(legacy_blob_name)
            if legacy_blob.exists():
                legacy_blob.delete()
                deleted = True
        
        if not deleted:
            raise ValueError(f"Garment {garment_id} not found")

    # =========================================================================
    # Legacy Data Migration Helpers
    # =========================================================================
    
    async def has_legacy_data(self) -> bool:
        """Check if there's any legacy (non-user-scoped) data."""
        # Check for legacy avatar
        legacy_avatar = self.bucket.blob(self.LEGACY_AVATAR_PATH)
        if legacy_avatar.exists():
            return True
        
        # Check for legacy garments
        blobs = list(self.client.list_blobs(
            self.bucket, 
            prefix=self.LEGACY_GARMENTS_PREFIX,
            max_results=1
        ))
        if blobs:
            return True
        
        return False
    
    async def migrate_legacy_data(self, target_user_id: str) -> dict:
        """
        Migrate all legacy data to a user's namespace.
        
        Args:
            target_user_id: User ID to migrate data to
        
        Returns:
            Migration summary with counts
        """
        summary = {
            "avatar_migrated": False,
            "garments_migrated": 0,
            "tryon_results_migrated": 0,
            "errors": []
        }
        
        logger.info(f"Starting legacy data migration to user: {target_user_id}")
        
        # Migrate avatar
        try:
            legacy_avatar = self.bucket.blob(self.LEGACY_AVATAR_PATH)
            if legacy_avatar.exists():
                avatar_bytes = legacy_avatar.download_as_bytes()
                new_blob_name = self._user_avatar_path(target_user_id)
                new_blob = self.bucket.blob(new_blob_name)
                new_blob.upload_from_string(avatar_bytes, content_type="image/png")
                legacy_avatar.delete()
                summary["avatar_migrated"] = True
                logger.info("Migrated legacy avatar")
        except Exception as e:
            summary["errors"].append(f"Avatar migration failed: {e}")
            logger.error(f"Avatar migration failed: {e}")
        
        # Migrate garments
        try:
            blobs = list(self.client.list_blobs(
                self.bucket, 
                prefix=self.LEGACY_GARMENTS_PREFIX
            ))
            
            for blob in blobs:
                if blob.name.endswith(".png"):
                    # Parse path: garments/{category}/{garment_id}.png
                    parts = blob.name.split("/")
                    if len(parts) >= 3:
                        category = parts[1]
                        garment_filename = parts[2]
                        
                        # Download and re-upload to user namespace
                        image_bytes = blob.download_as_bytes()
                        new_blob_name = f"users/{target_user_id}/garments/{category}/{garment_filename}"
                        new_blob = self.bucket.blob(new_blob_name)
                        new_blob.upload_from_string(image_bytes, content_type="image/png")
                        blob.delete()
                        summary["garments_migrated"] += 1
            
            logger.info(f"Migrated {summary['garments_migrated']} garments")
        except Exception as e:
            summary["errors"].append(f"Garment migration failed: {e}")
            logger.error(f"Garment migration failed: {e}")
        
        # Migrate try-on results
        try:
            blobs = list(self.client.list_blobs(
                self.bucket, 
                prefix=self.LEGACY_TRYON_PREFIX
            ))
            
            for blob in blobs:
                if blob.name.endswith(".png"):
                    result_id = blob.name.split("/")[-1].replace(".png", "")
                    
                    image_bytes = blob.download_as_bytes()
                    new_blob_name = self._user_tryon_path(target_user_id, result_id)
                    new_blob = self.bucket.blob(new_blob_name)
                    new_blob.upload_from_string(image_bytes, content_type="image/png")
                    blob.delete()
                    summary["tryon_results_migrated"] += 1
            
            logger.info(f"Migrated {summary['tryon_results_migrated']} try-on results")
        except Exception as e:
            summary["errors"].append(f"Try-on results migration failed: {e}")
            logger.error(f"Try-on results migration failed: {e}")
        
        logger.info(f"Migration complete: {summary}")
        return summary
