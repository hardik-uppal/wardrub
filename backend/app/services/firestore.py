"""Firestore service for persistent storage of profiles and garment metadata."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.logging_config import get_logger
from app.models.user_profile import UserProfile, UserProfileUpdate
from app.models.garment import GarmentMetadata
from app.models.daily_looks import DailyLooks

settings = get_settings()
logger = get_logger("firestore")

# In-memory fallback storage when Firestore isn't available
_memory_profiles: Dict[str, Dict[str, Any]] = {}
_memory_garments: Dict[str, Dict[str, Any]] = {}
_memory_daily_looks: Dict[str, Dict[str, Any]] = {}  # key: "{user_id}_{date}"


class FirestoreService:
    """Service for Firestore database operations with in-memory fallback."""
    
    # Collection names
    PROFILES_COLLECTION = "user_profiles"
    GARMENTS_COLLECTION = "garments"
    DAILY_LOOKS_COLLECTION = "daily_looks"
    
    # Legacy user ID (for migration purposes)
    LEGACY_USER_ID = "default_user"
    
    def __init__(self):
        """Initialize Firestore client."""
        self._client = None
        self._use_memory = False
    
    @property
    def client(self):
        """Lazy initialization of Firestore client."""
        if self._client is None and not self._use_memory:
            try:
                from google.cloud import firestore
                from google.oauth2 import service_account
                
                # Use 'wardrub' database instead of default
                database_id = "wardrub"
                
                if settings.GOOGLE_APPLICATION_CREDENTIALS:
                    credentials = service_account.Credentials.from_service_account_file(
                        settings.GOOGLE_APPLICATION_CREDENTIALS
                    )
                    self._client = firestore.Client(
                        project=settings.GOOGLE_CLOUD_PROJECT,
                        credentials=credentials,
                        database=database_id
                    )
                else:
                    # Use default credentials (for Cloud Run)
                    self._client = firestore.Client(
                        project=settings.GOOGLE_CLOUD_PROJECT,
                        database=database_id
                    )
                
                # Test connection
                self._client.collection("_test").limit(1).get()
                logger.info(f"Firestore client initialized (database: {database_id})")
            except Exception as e:
                logger.warning(f"Firestore unavailable, using in-memory storage: {e}")
                self._use_memory = True
                self._client = None
        return self._client
    
    # =========================================================================
    # User Profile Operations
    # =========================================================================
    
    async def get_user_profile(self, user_id: str = LEGACY_USER_ID) -> Optional[UserProfile]:
        """
        Get user profile from Firestore or memory.
        
        Args:
            user_id: User identifier (default for single-user app)
        
        Returns:
            UserProfile if exists, None otherwise
        """
        try:
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                data = _memory_profiles.get(user_id)
                if data:
                    return UserProfile(**data)
                return None
            
            doc_ref = self.client.collection(self.PROFILES_COLLECTION).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return UserProfile(**data)
            return None
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            # Try in-memory fallback
            data = _memory_profiles.get(user_id)
            if data:
                return UserProfile(**data)
            return None
    
    async def save_user_profile(
        self, 
        profile: UserProfile, 
        user_id: str = LEGACY_USER_ID
    ) -> bool:
        """
        Save or update user profile.
        
        Args:
            profile: UserProfile to save
            user_id: User identifier
        
        Returns:
            True if successful
        """
        try:
            profile.updated_at = datetime.utcnow()
            data = profile.model_dump()
            
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                _memory_profiles[user_id] = data
                logger.info(f"Saved user profile for {user_id} (in-memory)")
                return True
            
            doc_ref = self.client.collection(self.PROFILES_COLLECTION).document(user_id)
            doc_ref.set(data)
            logger.info(f"Saved user profile for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
            # Fallback to in-memory
            _memory_profiles[user_id] = profile.model_dump()
            logger.info(f"Saved user profile for {user_id} (fallback to in-memory)")
            return True
    
    async def update_user_profile(
        self, 
        updates: Dict[str, Any], 
        user_id: str = LEGACY_USER_ID
    ) -> bool:
        """
        Partially update user profile (creates if doesn't exist).
        
        Args:
            updates: Dictionary of fields to update
            user_id: User identifier
        
        Returns:
            True if successful
        """
        try:
            updates["updated_at"] = datetime.utcnow()
            
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                if user_id not in _memory_profiles:
                    _memory_profiles[user_id] = {}
                _memory_profiles[user_id].update(updates)
                logger.info(f"Updated user profile for {user_id} (in-memory)")
                return True
            
            doc_ref = self.client.collection(self.PROFILES_COLLECTION).document(user_id)
            # Use set with merge=True to create if doesn't exist
            doc_ref.set(updates, merge=True)
            logger.info(f"Updated user profile for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            # Fallback to in-memory
            if user_id not in _memory_profiles:
                _memory_profiles[user_id] = {}
            _memory_profiles[user_id].update(updates)
            logger.info(f"Updated user profile for {user_id} (fallback to in-memory)")
            return True
    
    async def delete_user_profile(self, user_id: str = LEGACY_USER_ID) -> bool:
        """Delete user profile."""
        try:
            doc_ref = self.client.collection(self.PROFILES_COLLECTION).document(user_id)
            doc_ref.delete()
            logger.info(f"Deleted user profile for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete user profile: {e}")
            return False
    
    # =========================================================================
    # Garment Metadata Operations
    # =========================================================================
    
    async def get_garment_metadata(self, garment_id: str) -> Optional[GarmentMetadata]:
        """
        Get garment metadata from Firestore or memory.
        
        Args:
            garment_id: Garment identifier
        
        Returns:
            GarmentMetadata if exists, None otherwise
        """
        try:
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                data = _memory_garments.get(garment_id)
                if data:
                    return GarmentMetadata(**data)
                return None
            
            doc_ref = self.client.collection(self.GARMENTS_COLLECTION).document(garment_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return GarmentMetadata(**data)
            return None
        except Exception as e:
            logger.error(f"Failed to get garment metadata: {e}")
            data = _memory_garments.get(garment_id)
            if data:
                return GarmentMetadata(**data)
            return None
    
    async def save_garment_metadata(self, metadata: GarmentMetadata) -> bool:
        """
        Save or update garment metadata.
        
        Args:
            metadata: GarmentMetadata to save
        
        Returns:
            True if successful
        """
        try:
            metadata.updated_at = datetime.utcnow()
            data = metadata.model_dump()
            
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                _memory_garments[metadata.garment_id] = data
                logger.info(f"Saved garment metadata for {metadata.garment_id} (in-memory)")
                return True
            
            doc_ref = self.client.collection(self.GARMENTS_COLLECTION).document(metadata.garment_id)
            doc_ref.set(data)
            logger.info(f"Saved garment metadata for {metadata.garment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save garment metadata: {e}")
            # Fallback to in-memory
            _memory_garments[metadata.garment_id] = metadata.model_dump()
            return True
    
    async def update_garment_metadata(
        self, 
        garment_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Partially update garment metadata.
        
        Args:
            garment_id: Garment identifier
            updates: Dictionary of fields to update
        
        Returns:
            True if successful
        """
        try:
            updates["updated_at"] = datetime.utcnow()
            doc_ref = self.client.collection(self.GARMENTS_COLLECTION).document(garment_id)
            doc_ref.update(updates)
            logger.info(f"Updated garment metadata for {garment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update garment metadata: {e}")
            return False
    
    async def delete_garment_metadata(self, garment_id: str) -> bool:
        """Delete garment metadata."""
        try:
            doc_ref = self.client.collection(self.GARMENTS_COLLECTION).document(garment_id)
            doc_ref.delete()
            logger.info(f"Deleted garment metadata for {garment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete garment metadata: {e}")
            return False
    
    async def list_garments_metadata(
        self, 
        user_id: str,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[GarmentMetadata]:
        """
        List all garment metadata for a user, optionally filtered by category.
        
        Args:
            user_id: User ID to filter by
            category: Optional category filter
            limit: Maximum number of results
        
        Returns:
            List of GarmentMetadata objects
        """
        try:
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                results = []
                for garment_id, data in list(_memory_garments.items())[:limit]:
                    try:
                        if data.get("user_id") != user_id:
                            continue
                        if category is None or data.get("category") == category:
                            results.append(GarmentMetadata(**data))
                    except Exception as e:
                        logger.warning(f"Failed to parse garment {garment_id}: {e}")
                return results
            
            collection_ref = self.client.collection(self.GARMENTS_COLLECTION)
            
            # Always filter by user_id
            query = collection_ref.where("user_id", "==", user_id)
            
            if category:
                query = query.where("category", "==", category)
            
            query = query.limit(limit)
            
            docs = query.stream()
            results = []
            
            for doc in docs:
                try:
                    data = doc.to_dict()
                    results.append(GarmentMetadata(**data))
                except Exception as e:
                    logger.warning(f"Failed to parse garment {doc.id}: {e}")
            
            return results
        except Exception as e:
            logger.error(f"Failed to list garments metadata: {e}")
            # Return in-memory as fallback
            results = []
            for garment_id, data in list(_memory_garments.items())[:limit]:
                try:
                    if data.get("user_id") != user_id:
                        continue
                    if category is None or data.get("category") == category:
                        results.append(GarmentMetadata(**data))
                except:
                    pass
            return results
    
    async def get_garments_with_scores(
        self,
        user_id: str,
        min_overall_score: float = 0.0,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[GarmentMetadata]:
        """
        Get garments filtered by recommendation score for a user.
        
        Args:
            user_id: User ID to filter by
            min_overall_score: Minimum overall recommendation score
            category: Optional category filter
            limit: Maximum results
        
        Returns:
            List of GarmentMetadata sorted by score
        """
        try:
            from google.cloud import firestore
            
            collection_ref = self.client.collection(self.GARMENTS_COLLECTION)
            query = collection_ref.where(
                "user_id", "==", user_id
            ).where(
                "recommendation_scores.overall", ">=", min_overall_score
            ).order_by(
                "recommendation_scores.overall", direction=firestore.Query.DESCENDING
            ).limit(limit)
            
            if category:
                query = query.where("category", "==", category)
            
            docs = query.stream()
            results = []
            
            for doc in docs:
                try:
                    data = doc.to_dict()
                    results.append(GarmentMetadata(**data))
                except Exception as e:
                    logger.warning(f"Failed to parse garment {doc.id}: {e}")
            
            return results
        except Exception as e:
            logger.error(f"Failed to get garments with scores: {e}")
            return []
    
    async def garment_has_metadata(self, garment_id: str) -> bool:
        """Check if garment has metadata in Firestore."""
        try:
            if self._use_memory or self.client is None:
                return garment_id in _memory_garments
            
            doc_ref = self.client.collection(self.GARMENTS_COLLECTION).document(garment_id)
            doc = doc_ref.get()
            return doc.exists
        except Exception as e:
            logger.error(f"Failed to check garment metadata: {e}")
            return garment_id in _memory_garments
    
    async def sync_garments_from_storage(
        self, 
        user_id: str,
        storage_garments: List[Dict[str, Any]]
    ) -> int:
        """
        Sync garments from cloud storage into the metadata store.
        
        This creates basic metadata for garments that exist in storage
        but don't have metadata yet. Useful for recommendations.
        
        Args:
            user_id: User ID who owns these garments
            storage_garments: List of garment dicts from storage service
        
        Returns:
            Number of garments synced
        """
        synced = 0
        
        for garment in storage_garments:
            garment_id = garment.get("id")
            if not garment_id:
                continue
            
            # Skip if already has metadata
            if await self.garment_has_metadata(garment_id):
                continue
            
            # Create basic metadata from storage info
            metadata = GarmentMetadata(
                garment_id=garment_id,
                user_id=user_id,
                category=garment.get("category", "top"),
                ghost_mannequin_url=garment.get("front_url"),
            )
            
            # Save to store (in-memory or Firestore)
            await self.save_garment_metadata(metadata)
            synced += 1
        
        if synced > 0:
            logger.info(f"Synced {synced} garments from storage to metadata store for user {user_id}")
        
        return synced
    
    async def list_garments_without_descriptions(
        self,
        user_id: Optional[str] = None
    ) -> List[GarmentMetadata]:
        """
        List garments that don't have detailed descriptions.
        
        Args:
            user_id: Optional user ID to filter by. If None, checks all garments.
        
        Returns:
            List of GarmentMetadata objects needing descriptions
        """
        try:
            # Get all garments (optionally filtered by user)
            if user_id:
                all_garments = await self.list_garments_metadata(user_id=user_id)
            else:
                # For backfill jobs, get all garments across all users
                if self._use_memory or self.client is None:
                    all_garments = [GarmentMetadata(**data) for data in _memory_garments.values()]
                else:
                    docs = self.client.collection(self.GARMENTS_COLLECTION).limit(500).stream()
                    all_garments = []
                    for doc in docs:
                        try:
                            all_garments.append(GarmentMetadata(**doc.to_dict()))
                        except:
                            pass
            
            # Filter garments without descriptions
            needs_description = []
            for garment in all_garments:
                if garment.description is None:
                    needs_description.append(garment)
                elif not garment.description.detailed or garment.description.detailed.strip() == "":
                    needs_description.append(garment)
                elif garment.description.short.startswith("Processed "):
                    # Placeholder descriptions from upload
                    needs_description.append(garment)
            
            logger.info(f"Found {len(needs_description)} garments without descriptions")
            return needs_description
            
        except Exception as e:
            logger.error(f"Failed to list garments without descriptions: {e}")
            return []
    
    async def update_garment_description(
        self,
        garment_id: str,
        description_data: Dict[str, Any]
    ) -> bool:
        """
        Update garment with description and related fields.
        
        Args:
            garment_id: Garment identifier
            description_data: Dictionary with description, fit_type, 
                            season_suitability, weather_range
        
        Returns:
            True if successful
        """
        try:
            updates = {
                "updated_at": datetime.utcnow()
            }
            
            # Handle description object
            if "description" in description_data:
                desc = description_data["description"]
                if hasattr(desc, "model_dump"):
                    updates["description"] = desc.model_dump()
                else:
                    updates["description"] = desc
            
            # Handle fit_type enum
            if "fit_type" in description_data:
                fit = description_data["fit_type"]
                if hasattr(fit, "value"):
                    updates["fit_type"] = fit.value
                else:
                    updates["fit_type"] = fit
            
            # Handle season_suitability list
            if "season_suitability" in description_data:
                updates["season_suitability"] = description_data["season_suitability"]
            
            # Handle weather_range object
            if "weather_range" in description_data:
                weather = description_data["weather_range"]
                if hasattr(weather, "model_dump"):
                    updates["weather_range"] = weather.model_dump()
                else:
                    updates["weather_range"] = weather
            
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                if garment_id in _memory_garments:
                    _memory_garments[garment_id].update(updates)
                    logger.info(f"Updated description for {garment_id} (in-memory)")
                    return True
                else:
                    logger.warning(f"Garment {garment_id} not found in memory")
                    return False
            
            doc_ref = self.client.collection(self.GARMENTS_COLLECTION).document(garment_id)
            doc_ref.update(updates)
            logger.info(f"Updated description for {garment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update garment description for {garment_id}: {e}")
            return False
    
    # =========================================================================
    # Daily Looks Operations
    # =========================================================================
    
    async def save_daily_looks(self, looks: DailyLooks) -> bool:
        """
        Save daily looks for a user.
        
        Args:
            looks: DailyLooks object to save
        
        Returns:
            True if successful
        """
        try:
            doc_id = f"{looks.user_id}_{looks.date}"
            data = looks.model_dump()
            
            # Convert datetime to ISO string for Firestore
            if isinstance(data.get("generated_at"), datetime):
                data["generated_at"] = data["generated_at"].isoformat()
            
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                _memory_daily_looks[doc_id] = data
                logger.info(f"Saved daily looks for {doc_id} (in-memory)")
                return True
            
            doc_ref = self.client.collection(self.DAILY_LOOKS_COLLECTION).document(doc_id)
            doc_ref.set(data)
            logger.info(f"Saved daily looks for {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save daily looks: {e}")
            # Fallback to in-memory
            doc_id = f"{looks.user_id}_{looks.date}"
            _memory_daily_looks[doc_id] = looks.model_dump()
            return True
    
    async def get_daily_looks(
        self,
        user_id: str,
        date: str
    ) -> Optional[DailyLooks]:
        """
        Get daily looks for a specific date.
        
        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
        
        Returns:
            DailyLooks if found, None otherwise
        """
        try:
            doc_id = f"{user_id}_{date}"
            
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                data = _memory_daily_looks.get(doc_id)
                if data:
                    return DailyLooks(**data)
                return None
            
            doc_ref = self.client.collection(self.DAILY_LOOKS_COLLECTION).document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return DailyLooks(**doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Failed to get daily looks for {user_id} on {date}: {e}")
            # Try in-memory fallback
            doc_id = f"{user_id}_{date}"
            data = _memory_daily_looks.get(doc_id)
            if data:
                return DailyLooks(**data)
            return None
    
    async def get_latest_daily_looks(
        self,
        user_id: str = LEGACY_USER_ID
    ) -> Optional[DailyLooks]:
        """
        Get the most recent daily looks for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Most recent DailyLooks if found, None otherwise
        """
        try:
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                # Find the most recent date for this user
                user_looks = [
                    (key, data) for key, data in _memory_daily_looks.items()
                    if key.startswith(f"{user_id}_")
                ]
                if not user_looks:
                    return None
                
                # Sort by date descending
                user_looks.sort(key=lambda x: x[0], reverse=True)
                return DailyLooks(**user_looks[0][1])
            
            # Simple approach: check recent days directly by document ID
            # This avoids needing a composite index
            from datetime import date, timedelta
            today = date.today()
            
            for days_ago in range(7):  # Check last 7 days
                check_date = (today - timedelta(days=days_ago)).isoformat()
                doc_id = f"{user_id}_{check_date}"
                
                doc_ref = self.client.collection(self.DAILY_LOOKS_COLLECTION).document(doc_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    return DailyLooks(**doc.to_dict())
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest daily looks for {user_id}: {e}")
            return None
    
    async def list_daily_looks(
        self,
        user_id: str = LEGACY_USER_ID,
        limit: int = 7
    ) -> List[DailyLooks]:
        """
        List recent daily looks for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of days to return
        
        Returns:
            List of DailyLooks, most recent first
        """
        try:
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                user_looks = [
                    DailyLooks(**data) for key, data in _memory_daily_looks.items()
                    if key.startswith(f"{user_id}_")
                ]
                user_looks.sort(key=lambda x: x.date, reverse=True)
                return user_looks[:limit]
            
            query = self.client.collection(self.DAILY_LOOKS_COLLECTION).where(
                "user_id", "==", user_id
            ).order_by(
                "date", direction="DESCENDING"
            ).limit(limit)
            
            docs = query.stream()
            return [DailyLooks(**doc.to_dict()) for doc in docs]
            
        except Exception as e:
            logger.error(f"Failed to list daily looks for {user_id}: {e}")
            return []
    
    async def delete_daily_looks(
        self,
        user_id: str,
        date: str
    ) -> bool:
        """
        Delete daily looks for a specific date.
        
        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
        
        Returns:
            True if deleted, False if not found
        """
        try:
            doc_id = f"{user_id}_{date}"
            
            # Use in-memory fallback
            if self._use_memory or self.client is None:
                if doc_id in _memory_daily_looks:
                    del _memory_daily_looks[doc_id]
                    logger.info(f"Deleted daily looks for {doc_id} (in-memory)")
                    return True
                return False
            
            doc_ref = self.client.collection(self.DAILY_LOOKS_COLLECTION).document(doc_id)
            doc_ref.delete()
            logger.info(f"Deleted daily looks for {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete daily looks for {user_id} on {date}: {e}")
            return False
    
    # =========================================================================
    # Legacy Data Migration
    # =========================================================================
    
    async def has_legacy_data(self) -> bool:
        """
        Check if there's any legacy garment/profile data without user_id.
        
        Returns:
            True if legacy data exists
        """
        try:
            # Check for legacy profile
            legacy_profile = await self.get_user_profile(self.LEGACY_USER_ID)
            if legacy_profile:
                return True
            
            # Check for garments without user_id
            if self._use_memory or self.client is None:
                for data in _memory_garments.values():
                    if not data.get("user_id"):
                        return True
            else:
                # Query for garments where user_id doesn't exist
                # Note: Firestore can't query for null fields easily,
                # so we check the legacy user or garments without the field
                docs = self.client.collection(self.GARMENTS_COLLECTION).limit(10).stream()
                for doc in docs:
                    data = doc.to_dict()
                    if not data.get("user_id"):
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to check for legacy data: {e}")
            return False
    
    async def migrate_legacy_firestore_data(self, target_user_id: str) -> dict:
        """
        Migrate all legacy Firestore data to a user's namespace.
        
        Args:
            target_user_id: User ID to migrate data to
        
        Returns:
            Migration summary with counts
        """
        summary = {
            "profile_migrated": False,
            "garments_migrated": 0,
            "daily_looks_migrated": 0,
            "errors": []
        }
        
        logger.info(f"Starting legacy Firestore migration to user: {target_user_id}")
        
        # Migrate legacy profile
        try:
            legacy_profile = await self.get_user_profile(self.LEGACY_USER_ID)
            if legacy_profile:
                await self.save_user_profile(legacy_profile, target_user_id)
                await self.delete_user_profile(self.LEGACY_USER_ID)
                summary["profile_migrated"] = True
                logger.info("Migrated legacy user profile")
        except Exception as e:
            summary["errors"].append(f"Profile migration failed: {e}")
            logger.error(f"Profile migration failed: {e}")
        
        # Migrate garments without user_id
        try:
            if self._use_memory or self.client is None:
                for garment_id, data in list(_memory_garments.items()):
                    if not data.get("user_id"):
                        data["user_id"] = target_user_id
                        _memory_garments[garment_id] = data
                        summary["garments_migrated"] += 1
            else:
                docs = self.client.collection(self.GARMENTS_COLLECTION).stream()
                for doc in docs:
                    data = doc.to_dict()
                    if not data.get("user_id"):
                        data["user_id"] = target_user_id
                        doc.reference.set(data)
                        summary["garments_migrated"] += 1
            
            logger.info(f"Migrated {summary['garments_migrated']} garments")
        except Exception as e:
            summary["errors"].append(f"Garment migration failed: {e}")
            logger.error(f"Garment migration failed: {e}")
        
        # Migrate legacy daily looks
        try:
            legacy_looks = await self.list_daily_looks(self.LEGACY_USER_ID, limit=100)
            for look in legacy_looks:
                look.user_id = target_user_id
                await self.save_daily_looks(look)
                await self.delete_daily_looks(self.LEGACY_USER_ID, look.date)
                summary["daily_looks_migrated"] += 1
            
            logger.info(f"Migrated {summary['daily_looks_migrated']} daily looks")
        except Exception as e:
            summary["errors"].append(f"Daily looks migration failed: {e}")
            logger.error(f"Daily looks migration failed: {e}")
        
        logger.info(f"Firestore migration complete: {summary}")
        return summary

