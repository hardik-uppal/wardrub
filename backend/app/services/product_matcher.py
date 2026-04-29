"""
Product Matching Service - Find similar products and extract rich metadata.

Uses Google Cloud Vision API to find visually similar products online,
then uses Gemini to extract detailed product information when user confirms a match.
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from io import BytesIO
from dataclasses import dataclass

from google.cloud import vision
from google.oauth2 import service_account

from app.config import get_settings
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger("product_matcher")


@dataclass
class SimilarProduct:
    """A visually similar product found online."""
    image_url: str
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ProductMatch:
    """Confirmed product match with extracted details."""
    source_url: str
    brand: Optional[str] = None
    product_name: Optional[str] = None
    material: Optional[str] = None
    fabric_composition: Optional[str] = None
    style: Optional[str] = None
    fit: Optional[str] = None
    care_instructions: Optional[str] = None
    occasion: List[str] = None
    season: List[str] = None
    description: str = ""
    features: List[str] = None
    price_range: Optional[str] = None
    
    def __post_init__(self):
        if self.occasion is None:
            self.occasion = []
        if self.season is None:
            self.season = []
        if self.features is None:
            self.features = []


class ProductMatcherService:
    """Service for finding and matching similar products."""
    
    def __init__(self):
        self._vision_client = None
    
    def _get_credentials(self):
        """Get GCP credentials."""
        creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
        if creds_path and os.path.exists(creds_path):
            return service_account.Credentials.from_service_account_file(creds_path)
        return None
    
    @property
    def vision_client(self) -> vision.ImageAnnotatorClient:
        """Lazy initialization of Vision API client."""
        if self._vision_client is None:
            credentials = self._get_credentials()
            if credentials:
                self._vision_client = vision.ImageAnnotatorClient(credentials=credentials)
            else:
                self._vision_client = vision.ImageAnnotatorClient()
        return self._vision_client
    
    async def find_similar_products(
        self, 
        image_bytes: bytes,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Find visually similar products online using Vision API.
        
        Args:
            image_bytes: The garment image bytes
            max_results: Maximum number of similar images to return
        
        Returns:
            Dict with similar_products, web_entities, and best_guess_labels
        """
        logger.info("🔍 Finding similar products with Vision API...")
        
        image = vision.Image(content=image_bytes)
        
        # Run web detection
        response = self.vision_client.web_detection(image=image)
        
        if response.error.message:
            logger.error(f"Vision API error: {response.error.message}")
            raise ValueError(f"Vision API error: {response.error.message}")
        
        annotations = response.web_detection
        
        result = {
            "similar_products": [],
            "web_entities": [],
            "best_guess_labels": [],
            "pages_with_matches": []
        }
        
        # Extract web entities (brands, product types)
        if annotations.web_entities:
            for entity in annotations.web_entities[:10]:
                if entity.description:
                    result["web_entities"].append({
                        "description": entity.description,
                        "score": entity.score
                    })
        
        # Extract best guess labels
        if annotations.best_guess_labels:
            result["best_guess_labels"] = [label.label for label in annotations.best_guess_labels]
        
        # Extract visually similar images
        if annotations.visually_similar_images:
            for img in annotations.visually_similar_images[:max_results]:
                result["similar_products"].append({
                    "image_url": img.url,
                    "confidence": 0.8  # Vision API doesn't give confidence for similar images
                })
        
        # Extract pages with matching images (often product pages)
        if annotations.pages_with_matching_images:
            for page in annotations.pages_with_matching_images[:5]:
                page_info = {
                    "url": page.url,
                    "title": page.page_title if page.page_title else None
                }
                # Get matching images from this page
                if page.full_matching_images:
                    page_info["matching_images"] = [img.url for img in page.full_matching_images[:3]]
                if page.partial_matching_images:
                    page_info["partial_matches"] = [img.url for img in page.partial_matching_images[:3]]
                result["pages_with_matches"].append(page_info)
        
        logger.info(f"✅ Found {len(result['similar_products'])} similar products, "
                   f"{len(result['web_entities'])} entities, "
                   f"{len(result['pages_with_matches'])} matching pages")
        
        return result
    
    async def extract_product_details(
        self,
        image_url: str,
        garment_category: str,
        original_image_bytes: Optional[bytes] = None
    ) -> ProductMatch:
        """
        Extract detailed product information from a confirmed match.
        Uses Gemini to analyze the product image and extract rich metadata.
        
        Args:
            image_url: URL of the confirmed similar product image
            garment_category: Category (top, bottom, dress, outerwear)
            original_image_bytes: Optional original garment image for comparison
        
        Returns:
            ProductMatch with extracted details
        """
        from google import genai
        from google.genai import types
        
        logger.info(f"📝 Extracting product details from: {image_url[:50]}...")
        
        # Download the product image
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url, follow_redirects=True)
                response.raise_for_status()
                product_image_bytes = response.content
        except Exception as e:
            logger.error(f"Failed to download product image: {e}")
            # Return basic match if can't download
            return ProductMatch(source_url=image_url, description="Unable to fetch product details")
        
        # Initialize Gemini client
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        if api_key:
            gemini_client = genai.Client(api_key=api_key)
        else:
            gemini_client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION
            )
        
        # Build prompt for detailed product analysis
        prompt = f"""Analyze this fashion product image and extract detailed information.

This is a {garment_category} garment. Please provide:

1. **Brand** (if visible or identifiable from style)
2. **Product Name/Type** (specific type like "slim-fit chinos", "A-line midi skirt", etc.)
3. **Material/Fabric** (cotton, polyester, silk, denim, etc.)
4. **Fabric Composition** (if identifiable, e.g., "100% cotton", "95% polyester 5% elastane")
5. **Style** (casual, formal, streetwear, athleisure, bohemian, minimalist, etc.)
6. **Fit** (slim, regular, relaxed, oversized, tailored)
7. **Care Instructions** (if inferable from material)
8. **Occasions** (work, casual, party, date night, workout, etc.)
9. **Seasons** (spring, summer, fall, winter, all-season)
10. **Key Features** (pockets, buttons, zipper, pleats, patterns, embroidery, etc.)
11. **Detailed Description** (2-3 sentences describing the garment comprehensively)
12. **Price Range** (budget, mid-range, premium, luxury - based on apparent quality)

Return as JSON:
{{
    "brand": "...",
    "product_name": "...",
    "material": "...",
    "fabric_composition": "...",
    "style": "...",
    "fit": "...",
    "care_instructions": "...",
    "occasions": ["...", "..."],
    "seasons": ["...", "..."],
    "features": ["...", "..."],
    "description": "...",
    "price_range": "..."
}}

Be specific and detailed. If something is not visible or identifiable, use your best judgment based on the garment's appearance."""

        contents = [
            prompt,
            types.Part.from_bytes(data=product_image_bytes, mime_type="image/jpeg")
        ]
        
        # If we have the original image, add it for comparison
        if original_image_bytes:
            contents.insert(1, "Reference - User's garment (for comparison):")
            contents.insert(2, types.Part.from_bytes(data=original_image_bytes, mime_type="image/png"))
            contents.insert(3, "Similar product found online:")
        
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
            )
            
            # Parse the response
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text.strip()
                                
                                # Clean JSON from markdown
                                if text.startswith("```json"):
                                    text = text[7:]
                                if text.startswith("```"):
                                    text = text[3:]
                                if text.endswith("```"):
                                    text = text[:-3]
                                text = text.strip()
                                
                                import json
                                data = json.loads(text)
                                
                                logger.info(f"✅ Extracted product details: {data.get('product_name', 'N/A')}")
                                
                                return ProductMatch(
                                    source_url=image_url,
                                    brand=data.get("brand"),
                                    product_name=data.get("product_name"),
                                    material=data.get("material"),
                                    fabric_composition=data.get("fabric_composition"),
                                    style=data.get("style"),
                                    fit=data.get("fit"),
                                    care_instructions=data.get("care_instructions"),
                                    occasion=data.get("occasions", []),
                                    season=data.get("seasons", []),
                                    features=data.get("features", []),
                                    description=data.get("description", ""),
                                    price_range=data.get("price_range")
                                )
            
            logger.warning("Gemini didn't return expected format")
            return ProductMatch(source_url=image_url, description="Unable to extract details")
            
        except Exception as e:
            logger.error(f"Failed to extract product details: {e}")
            return ProductMatch(source_url=image_url, description=f"Error: {str(e)}")
    
    async def get_enhanced_garment_info(
        self,
        image_bytes: bytes,
        category: str
    ) -> Dict[str, Any]:
        """
        Full pipeline: Find similar products and extract details from best match.
        
        Args:
            image_bytes: The garment image bytes
            category: Garment category
        
        Returns:
            Dict with similar_products and auto-extracted details from best match
        """
        # Step 1: Find similar products
        similar = await self.find_similar_products(image_bytes)
        
        result = {
            "similar_products": similar["similar_products"],
            "web_entities": similar["web_entities"],
            "best_guess_labels": similar["best_guess_labels"],
            "auto_extracted_details": None
        }
        
        # Step 2: Auto-extract details from first similar product (if any)
        if similar["similar_products"]:
            best_match_url = similar["similar_products"][0]["image_url"]
            try:
                details = await self.extract_product_details(
                    image_url=best_match_url,
                    garment_category=category,
                    original_image_bytes=image_bytes
                )
                result["auto_extracted_details"] = {
                    "source_url": details.source_url,
                    "brand": details.brand,
                    "product_name": details.product_name,
                    "material": details.material,
                    "fabric_composition": details.fabric_composition,
                    "style": details.style,
                    "fit": details.fit,
                    "care_instructions": details.care_instructions,
                    "occasions": details.occasion,
                    "seasons": details.season,
                    "features": details.features,
                    "description": details.description,
                    "price_range": details.price_range
                }
            except Exception as e:
                logger.error(f"Auto-extraction failed: {e}")
        
        return result


# Singleton instance
product_matcher = ProductMatcherService()
