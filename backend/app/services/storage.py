"""Google Cloud Storage service for image storage and retrieval."""

import uuid
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from io import BytesIO

from google.cloud import storage
from google.oauth2 import service_account
from PIL import Image, ImageOps

from app.config import get_settings
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger("storage")

import os

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "local_storage")

class PersistentMemoryFiles(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if getattr(self, "_disabled", False):
            return
        filepath = os.path.join(STORAGE_DIR, *key.split("/"))
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(value)
        except Exception as e:
            logger.warning(f"Failed to save file to local mock storage: {e}")

    def __delitem__(self, key):
        super().__delitem__(key)
        filepath = os.path.join(STORAGE_DIR, *key.split("/"))
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            pass

    def pop(self, key, default=None):
        res = super().pop(key, default)
        filepath = os.path.join(STORAGE_DIR, *key.split("/"))
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            pass
        return res

# In-memory storage mock when GCS is unavailable
_memory_files = PersistentMemoryFiles()
_memory_signed_urls: dict[str, str] = {}
_memory_look_metadata: dict[str, dict] = {}

def load_local_storage():
    if os.path.exists(STORAGE_DIR):
        try:
            _memory_files._disabled = True
            for root, dirs, files in os.walk(STORAGE_DIR):
                for file in files:
                    filepath = os.path.join(root, file)
                    relpath = os.path.relpath(filepath, STORAGE_DIR)
                    blob_name = relpath.replace(os.path.sep, "/")
                    with open(filepath, "rb") as f:
                        _memory_files[blob_name] = f.read()
                        _memory_signed_urls[blob_name] = f"/api/mock-gcs/{blob_name}"
            logger.info("Loaded local mock GCS files from disk")
        except Exception as e:
            logger.warning(f"Failed to load local storage files: {e}")
        finally:
            _memory_files._disabled = False

# Load mock files on module load
load_local_storage()


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

    def get_mock_file(self, blob_name: str) -> Optional[bytes]:
        """Get a file from in-memory mock storage."""
        return _memory_files.get(blob_name)
    
    @property
    def client(self) -> Optional[storage.Client]:
        """Lazy initialization of GCS client."""
        if self._client is None:
            has_creds_file = False
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                    has_creds_file = True
                else:
                    logger.warning(f"GCP credentials file not found at: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
            
            try:
                if has_creds_file:
                    credentials = service_account.Credentials.from_service_account_file(
                        settings.GOOGLE_APPLICATION_CREDENTIALS
                    )
                    self._client = storage.Client(
                        project=settings.GOOGLE_CLOUD_PROJECT,
                        credentials=credentials
                    )
                else:
                    # Try using application default credentials, but catch any error
                    self._client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
            except Exception as e:
                logger.warning(f"Could not initialize GCS client: {e}. Falling back to in-memory mock storage.")
                self._client = None
        return self._client
    
    @property
    def bucket(self) -> Optional[storage.Bucket]:
        """Get the configured GCS bucket."""
        if self._bucket is None:
            client = self.client
            if client is not None:
                try:
                    self._bucket = client.bucket(settings.GCS_BUCKET)
                except Exception as e:
                    logger.warning(f"Failed to get GCS bucket: {e}")
                    self._bucket = None
        return self._bucket
    
    def _generate_signed_url(self, blob_name: str, expiration_hours: int = 24) -> str:
        """Generate a signed URL for accessing a blob."""
        if self.bucket is None:
            return _memory_signed_urls.get(blob_name, f"/api/mock-gcs/{blob_name}")
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

    @staticmethod
    def _thumbnail_path(blob_name: str) -> str:
        stem, _ = os.path.splitext(blob_name)
        return f"{stem}_thumb.webp"

    @staticmethod
    def _create_thumbnail(image_bytes: bytes, max_size: int = 480) -> Optional[bytes]:
        """Create a compact display derivative while retaining the original asset."""
        try:
            with Image.open(BytesIO(image_bytes)) as source:
                image = ImageOps.exif_transpose(source)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA" if "transparency" in image.info else "RGB")
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                output = BytesIO()
                image.save(output, format="WEBP", quality=80, method=6)
                return output.getvalue()
        except Exception as error:
            logger.warning(f"Could not create image thumbnail: {error}")
            return None

    def _backfill_gcs_thumbnail(self, original_blob_name: str) -> Optional[str]:
        """Create a missing derivative for assets uploaded before thumbnail support."""
        try:
            original_blob = self.bucket.blob(original_blob_name)
            thumbnail_bytes = self._create_thumbnail(original_blob.download_as_bytes())
            if not thumbnail_bytes:
                return None
            thumbnail_name = self._thumbnail_path(original_blob_name)
            thumbnail_blob = self.bucket.blob(thumbnail_name)
            thumbnail_blob.metadata = original_blob.metadata
            thumbnail_blob.upload_from_string(thumbnail_bytes, content_type="image/webp")
            return self._generate_signed_url(thumbnail_name)
        except Exception as error:
            logger.warning(f"Could not backfill thumbnail for {original_blob_name}: {error}")
            return None
    
    async def upload_garment(
        self, 
        image_bytes: bytes, 
        garment_id: str, 
        category: str,
        user_id: str
    ) -> str:
        """
        Upload a processed garment image to GCS.
        """
        blob_name = self._user_garment_path(user_id, category, garment_id)
        thumbnail_name = self._thumbnail_path(blob_name)
        thumbnail_bytes = self._create_thumbnail(image_bytes)
        if self.bucket is None:
            url = f"/api/mock-gcs/{blob_name}"
            _memory_files[blob_name] = image_bytes
            _memory_signed_urls[blob_name] = url
            if thumbnail_bytes:
                _memory_files[thumbnail_name] = thumbnail_bytes
                _memory_signed_urls[thumbnail_name] = f"/api/mock-gcs/{thumbnail_name}"
            logger.info(f"Mock uploaded garment to {url} (in-memory)")
            return url
            
        blob = self.bucket.blob(blob_name)
        blob.metadata = {
            "category": category,
            "garment_id": garment_id,
            "user_id": user_id
        }
        blob.upload_from_string(image_bytes, content_type="image/png")
        if thumbnail_bytes:
            thumbnail_blob = self.bucket.blob(thumbnail_name)
            thumbnail_blob.metadata = blob.metadata
            thumbnail_blob.upload_from_string(thumbnail_bytes, content_type="image/webp")
        return self._generate_signed_url(blob_name)
    
    async def upload_avatar(self, image_bytes: bytes, user_id: str) -> str:
        """
        Upload a generated avatar image to GCS.
        """
        blob_name = self._user_avatar_path(user_id)
        if self.bucket is None:
            url = f"/api/mock-gcs/{blob_name}"
            _memory_files[blob_name] = image_bytes
            _memory_signed_urls[blob_name] = url
            logger.info(f"Mock uploaded avatar to {url} (in-memory)")
            return url
            
        blob = self.bucket.blob(blob_name)
        blob.metadata = {"user_id": user_id}
        blob.upload_from_string(image_bytes, content_type="image/png")
        return self._generate_signed_url(blob_name)
    
    async def upload_tryon_result(
        self,
        image_bytes: bytes,
        user_id: str,
        garment_ids: Optional[List[str]] = None,
        garment_categories: Optional[List[str]] = None,
    ) -> str:
        """
        Upload a try-on result image to GCS.
        """
        result_id = str(uuid.uuid4())
        blob_name = self._user_tryon_path(user_id, result_id)
        metadata = {
            "user_id": user_id,
            "result_id": result_id,
            "garment_ids": ",".join(garment_ids or []),
            "garment_categories": ",".join(garment_categories or []),
            "favorite": "false",
            "occasion": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        thumbnail_name = self._thumbnail_path(blob_name)
        thumbnail_bytes = self._create_thumbnail(image_bytes)
        if self.bucket is None:
            url = f"/api/mock-gcs/{blob_name}"
            _memory_files[blob_name] = image_bytes
            _memory_signed_urls[blob_name] = url
            _memory_look_metadata[blob_name] = metadata
            if thumbnail_bytes:
                _memory_files[thumbnail_name] = thumbnail_bytes
                _memory_signed_urls[thumbnail_name] = f"/api/mock-gcs/{thumbnail_name}"
            logger.info(f"Mock uploaded try-on result to {url} (in-memory)")
            return url
            
        blob = self.bucket.blob(blob_name)
        blob.metadata = metadata
        blob.upload_from_string(image_bytes, content_type="image/png")
        if thumbnail_bytes:
            thumbnail_blob = self.bucket.blob(thumbnail_name)
            thumbnail_blob.metadata = metadata
            thumbnail_blob.upload_from_string(thumbnail_bytes, content_type="image/webp")
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
        """
        blob_name = f"users/{user_id}/sources/{garment_id}_{view}.png"
        if self.bucket is None:
            url = f"/api/mock-gcs/{blob_name}"
            _memory_files[blob_name] = image_bytes
            _memory_signed_urls[blob_name] = url
            logger.info(f"Mock uploaded source image to {url} (in-memory)")
            return url
            
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
        """
        blob_name = f"users/{user_id}/avatar_sources/{source_type}.png"
        if self.bucket is None:
            url = f"/api/mock-gcs/{blob_name}"
            _memory_files[blob_name] = image_bytes
            _memory_signed_urls[blob_name] = url
            logger.info(f"Mock uploaded avatar source to {url} (in-memory)")
            return url
            
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
        """
        blob_name = self._user_avatar_path(user_id)
        if self.bucket is None:
            return _memory_signed_urls.get(blob_name)
            
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            return self._generate_signed_url(blob_name)
        return None
    
    async def delete_avatar(self, user_id: str) -> None:
        """
        Delete a user's avatar.
        """
        blob_name = self._user_avatar_path(user_id)
        if self.bucket is None:
            _memory_files.pop(blob_name, None)
            _memory_signed_urls.pop(blob_name, None)
            logger.info(f"Mock deleted avatar for {user_id}")
            return
            
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
    
    async def list_garments(self, user_id: str, category: Optional[str] = None) -> List[dict]:
        """
        List all garments in a user's wardrobe, grouped by garment ID.
        """
        if self.bucket is None:
            prefix = f"users/{user_id}/garments/{category}/" if category else f"users/{user_id}/garments/"
            garment_map = {}
            for name, val in list(_memory_files.items()):
                if name.startswith(prefix) and name.endswith(".png"):
                    parts = name.split("/")
                    if len(parts) >= 5:
                        cat = parts[3]
                        full_id = parts[4].replace(".png", "")
                        
                        if full_id.endswith("_front"):
                            base_id = full_id[:-6]
                            view = "front"
                        elif full_id.endswith("_back"):
                            base_id = full_id[:-5]
                            view = "back"
                        else:
                            base_id = full_id
                            view = "front"
                            
                        if base_id not in garment_map:
                            garment_map[base_id] = {
                                "id": base_id,
                                "category": cat,
                                "front_url": None,
                                "back_url": None,
                                "thumbnail_url": None,
                                "back_thumbnail_url": None,
                                "url": None
                            }
                            
                        url = _memory_signed_urls.get(name, f"/api/mock-gcs/{name}")
                        if view == "front":
                            garment_map[base_id]["front_url"] = url
                            garment_map[base_id]["url"] = url
                            thumbnail_name = self._thumbnail_path(name)
                            thumbnail_url = _memory_signed_urls.get(thumbnail_name)
                            if not thumbnail_url:
                                thumbnail_bytes = self._create_thumbnail(val)
                                if thumbnail_bytes:
                                    _memory_files[thumbnail_name] = thumbnail_bytes
                                    thumbnail_url = f"/api/mock-gcs/{thumbnail_name}"
                                    _memory_signed_urls[thumbnail_name] = thumbnail_url
                            garment_map[base_id]["thumbnail_url"] = thumbnail_url
                        else:
                            garment_map[base_id]["back_url"] = url
                            thumbnail_name = self._thumbnail_path(name)
                            garment_map[base_id]["back_thumbnail_url"] = _memory_signed_urls.get(
                                thumbnail_name
                            )
            return list(garment_map.values())
            
        if category:
            prefix = f"users/{user_id}/garments/{category}/"
        else:
            prefix = f"users/{user_id}/garments/"
        
        blobs = list(self.client.list_blobs(self.bucket, prefix=prefix))
        blob_names = {blob.name for blob in blobs}
        garment_map = {}
        for blob in blobs:
            if blob.name.endswith(".png"):
                parts = blob.name.split("/")
                if len(parts) >= 5:
                    cat = parts[3]
                    full_id = parts[4].replace(".png", "")
                    
                    if full_id.endswith("_front"):
                        base_id = full_id[:-6]
                        view = "front"
                    elif full_id.endswith("_back"):
                        base_id = full_id[:-5]
                        view = "back"
                    else:
                        base_id = full_id
                        view = "front"
                    
                    if base_id not in garment_map:
                        garment_map[base_id] = {
                            "id": base_id,
                            "category": cat,
                            "front_url": None,
                            "back_url": None,
                            "thumbnail_url": None,
                            "back_thumbnail_url": None,
                            "url": None
                        }
                    
                    url = self._generate_signed_url(blob.name)
                    if view == "front":
                        garment_map[base_id]["front_url"] = url
                        garment_map[base_id]["url"] = url
                        thumbnail_name = self._thumbnail_path(blob.name)
                        if thumbnail_name in blob_names:
                            garment_map[base_id]["thumbnail_url"] = self._generate_signed_url(
                                thumbnail_name
                            )
                        else:
                            garment_map[base_id]["thumbnail_url"] = self._backfill_gcs_thumbnail(
                                blob.name
                            )
                    else:
                        garment_map[base_id]["back_url"] = url
                        thumbnail_name = self._thumbnail_path(blob.name)
                        if thumbnail_name in blob_names:
                            garment_map[base_id]["back_thumbnail_url"] = self._generate_signed_url(
                                thumbnail_name
                            )
        
        return list(garment_map.values())
    
    async def list_tryon_results(self, user_id: str, limit: int = 50) -> List[dict]:
        """
        List recent try-on results (looks) for a user.
        """
        if self.bucket is None:
            prefix = f"users/{user_id}/tryon-results/"
            results = []
            for name, val in list(_memory_files.items()):
                if name.startswith(prefix) and name.endswith(".png"):
                    result_id = name.split("/")[-1].replace(".png", "")
                    thumbnail_name = self._thumbnail_path(name)
                    thumbnail_url = _memory_signed_urls.get(thumbnail_name)
                    if not thumbnail_url:
                        thumbnail_bytes = self._create_thumbnail(val)
                        if thumbnail_bytes:
                            _memory_files[thumbnail_name] = thumbnail_bytes
                            thumbnail_url = f"/api/mock-gcs/{thumbnail_name}"
                            _memory_signed_urls[thumbnail_name] = thumbnail_url
                    results.append({
                        "id": result_id,
                        "url": _memory_signed_urls.get(name, f"/api/mock-gcs/{name}"),
                        "thumbnail_url": thumbnail_url,
                        **self._format_look_metadata(_memory_look_metadata.get(name, {})),
                    })
            return self._sort_looks(results)[:limit]
            
        prefix = f"users/{user_id}/tryon-results/"
        blobs = list(self.client.list_blobs(
            self.bucket, 
            prefix=prefix,
        ))
        blob_names = {blob.name for blob in blobs}
        
        results = []
        for blob in blobs:
            if blob.name.endswith(".png"):
                result_id = blob.name.split("/")[-1].replace(".png", "")
                blob_metadata = blob.metadata or {}
                results.append({
                    "id": result_id,
                    "url": self._generate_signed_url(blob.name),
                    "thumbnail_url": (
                        self._generate_signed_url(self._thumbnail_path(blob.name))
                        if self._thumbnail_path(blob.name) in blob_names
                        else self._backfill_gcs_thumbnail(blob.name)
                    ),
                    **self._format_look_metadata({
                        **blob_metadata,
                        "created_at": (
                            blob_metadata.get("created_at")
                            or (blob.time_created.isoformat() if blob.time_created else "")
                        ),
                    }),
                })
        
        return self._sort_looks(results)[:limit]

    @staticmethod
    def _format_look_metadata(metadata: dict) -> dict:
        """Normalize persisted string metadata for API clients."""
        return {
            "created_at": metadata.get("created_at") or None,
            "favorite": str(metadata.get("favorite", "false")).lower() == "true",
            "occasion": metadata.get("occasion") or None,
            "garment_ids": [
                item for item in str(metadata.get("garment_ids", "")).split(",") if item
            ],
            "garment_categories": [
                item for item in str(metadata.get("garment_categories", "")).split(",") if item
            ],
        }

    @staticmethod
    def _sort_looks(looks: List[dict]) -> List[dict]:
        return sorted(
            looks,
            key=lambda look: look.get("created_at") or "",
            reverse=True,
        )

    async def update_look_metadata(
        self,
        look_id: str,
        user_id: str,
        favorite: Optional[bool] = None,
        occasion: Optional[str] = None,
    ) -> dict:
        """Update user-editable metadata attached to a saved look."""
        blob_name = self._user_tryon_path(user_id, look_id)

        if self.bucket is None:
            if blob_name not in _memory_files:
                raise ValueError(f"Look {look_id} not found")
            metadata = dict(_memory_look_metadata.get(blob_name, {}))
            if favorite is not None:
                metadata["favorite"] = str(favorite).lower()
            if occasion is not None:
                metadata["occasion"] = occasion
            _memory_look_metadata[blob_name] = metadata
            return self._format_look_metadata(metadata)

        blob = self.bucket.blob(blob_name)
        if not blob.exists():
            raise ValueError(f"Look {look_id} not found")
        blob.reload()
        metadata = dict(blob.metadata or {})
        if favorite is not None:
            metadata["favorite"] = str(favorite).lower()
        if occasion is not None:
            metadata["occasion"] = occasion
        blob.metadata = metadata
        blob.patch()
        return self._format_look_metadata(metadata)
    
    async def delete_look(self, look_id: str, user_id: str) -> None:
        """
        Delete a saved look (try-on result).
        """
        blob_name = self._user_tryon_path(user_id, look_id)
        thumbnail_name = self._thumbnail_path(blob_name)
        if self.bucket is None:
            if blob_name in _memory_files:
                _memory_files.pop(blob_name, None)
                _memory_signed_urls.pop(blob_name, None)
                _memory_look_metadata.pop(blob_name, None)
                _memory_files.pop(thumbnail_name, None)
                _memory_signed_urls.pop(thumbnail_name, None)
                logger.info(f"Mock deleted look {look_id}")
                return
            raise ValueError(f"Look {look_id} not found")
            
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
            thumbnail_blob = self.bucket.blob(thumbnail_name)
            if thumbnail_blob.exists():
                thumbnail_blob.delete()
        else:
            raise ValueError(f"Look {look_id} not found")
            
    async def download_image(self, url: str) -> bytes:
        """
        Download an image from a URL (handles signed URLs, gs:// paths, and mocks).
        """
        if self.bucket is None or "mock-gcs.wardrub.test" in url or "api/mock-gcs" in url:
            for path, val in _memory_signed_urls.items():
                if val == url or url.endswith(path):
                    return _memory_files.get(path, b"")
            if url.startswith("http"):
                import urllib.request
                try:
                    with urllib.request.urlopen(url) as response:
                        return response.read()
                except Exception as e:
                    logger.error(f"Failed mock download: {e}")
            return b""
            
        if url.startswith("gs://"):
            path = url.replace(f"gs://{settings.GCS_BUCKET}/", "")
            blob = self.bucket.blob(path)
            return blob.download_as_bytes()
        else:
            import re
            match = re.search(rf"{settings.GCS_BUCKET}/([^?]+)", url)
            if match:
                blob_name = match.group(1)
                blob = self.bucket.blob(blob_name)
                return blob.download_as_bytes()
            
            import urllib.request
            with urllib.request.urlopen(url) as response:
                return response.read()
    
    async def delete_garment(self, garment_id: str, user_id: str) -> None:
        """
        Delete a garment from storage (both front and back images).
        """
        if self.bucket is None:
            deleted = False
            for category in ["top", "bottom", "dress", "outerwear"]:
                for suffix in ["_front", "_back", ""]:
                    full_id = f"{garment_id}{suffix}"
                    blob_name = self._user_garment_path(user_id, category, full_id)
                    if blob_name in _memory_files:
                        _memory_files.pop(blob_name, None)
                        _memory_signed_urls.pop(blob_name, None)
                        thumbnail_name = self._thumbnail_path(blob_name)
                        _memory_files.pop(thumbnail_name, None)
                        _memory_signed_urls.pop(thumbnail_name, None)
                        deleted = True
            if not deleted:
                raise ValueError(f"Garment {garment_id} not found")
            logger.info(f"Mock deleted garment {garment_id}")
            return
            
        deleted = False
        for category in ["top", "bottom", "dress", "outerwear"]:
            front_blob_name = self._user_garment_path(user_id, category, f"{garment_id}_front")
            front_blob = self.bucket.blob(front_blob_name)
            if front_blob.exists():
                front_blob.delete()
                front_thumbnail = self.bucket.blob(self._thumbnail_path(front_blob_name))
                if front_thumbnail.exists():
                    front_thumbnail.delete()
                deleted = True
            
            back_blob_name = self._user_garment_path(user_id, category, f"{garment_id}_back")
            back_blob = self.bucket.blob(back_blob_name)
            if back_blob.exists():
                back_blob.delete()
                back_thumbnail = self.bucket.blob(self._thumbnail_path(back_blob_name))
                if back_thumbnail.exists():
                    back_thumbnail.delete()
                deleted = True
            
            legacy_blob_name = self._user_garment_path(user_id, category, garment_id)
            legacy_blob = self.bucket.blob(legacy_blob_name)
            if legacy_blob.exists():
                legacy_blob.delete()
                legacy_thumbnail = self.bucket.blob(self._thumbnail_path(legacy_blob_name))
                if legacy_thumbnail.exists():
                    legacy_thumbnail.delete()
                deleted = True
        
        if not deleted:
            raise ValueError(f"Garment {garment_id} not found")
            
    async def has_legacy_data(self) -> bool:
        """Check if there's any legacy (non-user-scoped) data."""
        if self.bucket is None:
            return self.LEGACY_AVATAR_PATH in _memory_files
            
        legacy_avatar = self.bucket.blob(self.LEGACY_AVATAR_PATH)
        if legacy_avatar.exists():
            return True
        
        blobs = list(self.client.list_blobs(
            self.bucket, 
            prefix=self.LEGACY_GARMENTS_PREFIX,
            max_results=1
        ))
        return len(blobs) > 0
    
    async def migrate_legacy_data(self, target_user_id: str) -> dict:
        """
        Migrate all legacy data to a user's namespace.
        """
        summary = {
            "avatar_migrated": False,
            "garments_migrated": 0,
            "tryon_results_migrated": 0,
            "errors": []
        }
        
        logger.info(f"Starting legacy data migration to user: {target_user_id}")
        
        if self.bucket is None:
            legacy_avatar = self.LEGACY_AVATAR_PATH
            if legacy_avatar in _memory_files:
                target_avatar = self._user_avatar_path(target_user_id)
                _memory_files[target_avatar] = _memory_files.pop(legacy_avatar)
                _memory_signed_urls[target_avatar] = f"/api/mock-gcs/{target_avatar}"
                summary["avatar_migrated"] = True
                logger.info("Migrated mock legacy avatar")
            return summary
            
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
                    parts = blob.name.split("/")
                    if len(parts) >= 3:
                        category = parts[1]
                        garment_filename = parts[2]
                        
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
