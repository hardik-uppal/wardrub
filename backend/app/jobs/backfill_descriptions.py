"""Backfill job to populate garment descriptions for existing items."""

import asyncio
from typing import Optional

from app.logging_config import get_logger
from app.services.firestore import FirestoreService
from app.services.storage import StorageService
from app.services.description_service import DescriptionService

logger = get_logger("backfill_descriptions")


async def backfill_garment_descriptions(
    batch_size: int = 10,
    delay_between_items: float = 0.5,
    delay_between_batches: float = 5.0,
    max_items: Optional[int] = None
) -> int:
    """
    Backfill descriptions for garments that don't have them.
    
    This job:
    1. Lists all garments without detailed descriptions
    2. Downloads each garment's image from GCS
    3. Analyzes it with Gemini to generate description
    4. Updates the garment metadata in Firestore
    
    Args:
        batch_size: Number of items to process before a longer pause
        delay_between_items: Seconds to wait between API calls (rate limiting)
        delay_between_batches: Seconds to wait between batches
        max_items: Maximum number of items to process (None = all)
    
    Returns:
        Number of garments updated
    """
    logger.info("Starting garment description backfill job...")
    
    firestore = FirestoreService()
    storage = StorageService()
    description_service = DescriptionService()
    
    # Get garments needing descriptions
    garments = await firestore.list_garments_without_descriptions()
    
    if not garments:
        logger.info("No garments need description backfill")
        return 0
    
    # Limit if max_items is specified
    if max_items:
        garments = garments[:max_items]
    
    total = len(garments)
    logger.info(f"Found {total} garments to backfill")
    
    updated = 0
    failed = 0
    
    for i, garment in enumerate(garments):
        try:
            # Get image URL
            image_url = garment.ghost_mannequin_url
            if not image_url and garment.source_images:
                image_url = garment.source_images[0].url if garment.source_images else None
            
            if not image_url:
                logger.warning(f"Skipping {garment.garment_id}: No image URL available")
                failed += 1
                continue
            
            logger.info(f"[{i+1}/{total}] Processing {garment.garment_id} ({garment.category})...")
            
            # Download image
            try:
                image_bytes = await storage.download_image(image_url)
            except Exception as e:
                logger.warning(f"Failed to download image for {garment.garment_id}: {e}")
                failed += 1
                continue
            
            # Analyze with Gemini
            description_data = await description_service.analyze_garment_description(
                image_bytes,
                garment.category if isinstance(garment.category, str) else garment.category.value
            )
            
            # Update Firestore
            success = await firestore.update_garment_description(
                garment.garment_id,
                description_data
            )
            
            if success:
                updated += 1
                short_desc = description_data["description"].short[:50]
                logger.info(f"  Updated: {short_desc}...")
            else:
                failed += 1
                logger.warning(f"  Failed to update {garment.garment_id}")
            
            # Rate limiting
            if i < total - 1:
                await asyncio.sleep(delay_between_items)
                
                # Batch pause
                if (i + 1) % batch_size == 0:
                    logger.info(f"Batch complete ({i+1}/{total}). Pausing for {delay_between_batches}s...")
                    await asyncio.sleep(delay_between_batches)
        
        except Exception as e:
            logger.error(f"Error processing {garment.garment_id}: {e}")
            failed += 1
            continue
    
    logger.info(f"Backfill complete: {updated} updated, {failed} failed out of {total}")
    return updated


async def run_backfill_if_needed() -> int:
    """
    Run backfill only if there are garments without descriptions.
    This is called on server startup.
    
    Returns:
        Number of garments updated
    """
    try:
        firestore = FirestoreService()
        garments = await firestore.list_garments_without_descriptions()
        
        if not garments:
            logger.info("Startup check: No garments need description backfill")
            return 0
        
        logger.info(f"Startup check: Found {len(garments)} garments needing descriptions")
        
        # Run backfill in background
        return await backfill_garment_descriptions()
        
    except Exception as e:
        logger.error(f"Backfill startup check failed: {e}")
        return 0

