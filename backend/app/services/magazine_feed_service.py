"""Magazine Feed Service - curates personalized editorial feeds using Gemini."""

import os
import json
import uuid
import random
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.logging_config import get_logger
from app.models.user_profile import UserProfile
from app.models.garment import GarmentMetadata
from app.models.magazine_feed import LookCard, MagazineFeed, SwapSuggestion, LookFeedback
from app.services.firestore import FirestoreService
from app.services.weather import WeatherService
from app.services.outfit_scorer import OutfitScorerService

settings = get_settings()
logger = get_logger("magazine_feed_service")


class MagazineFeedService:
    """Service to generate and manage personalized style magazine feeds."""

    def __init__(self):
        self.firestore = FirestoreService()
        self.weather_service = WeatherService()
        self.scorer = OutfitScorerService()

    def _get_gemini_client(self):
        """Configure and return the Google GenAI client."""
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            return genai.Client(api_key=api_key)
        else:
            return genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION
            )

    async def generate_magazine_feed(
        self,
        user_id: str,
        force_regenerate: bool = False
    ) -> Optional[MagazineFeed]:
        """
        Curates today's personalized fashion feed.
        
        Steps:
        1. Fetch user profile, weather, and garments.
        2. Ensure user has at least 5 garments.
        3. Score standard combinations to find top outfit candidates.
        4. Select a versatile garment (for 'One Item, Three Ways') and an underused garment.
        5. Invoke Gemini 2.0 to write Vogue-style copy and structure the final looks.
        6. Save the resulting MagazineFeed to Firestore.
        """
        today_str = date.today().isoformat()
        
        # Check cache unless force requested
        if not force_regenerate:
            cached_feed = await self.firestore.get_magazine_feed(user_id, today_str)
            if cached_feed:
                logger.info(f"Returning cached magazine feed for {user_id} on {today_str}")
                return cached_feed

        logger.info(f"Starting magazine feed generation for user {user_id}...")

        # 1. Fetch dependencies
        user_profile = await self.firestore.get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"No user profile found for {user_id}")
            return None

        # Fetch garments
        garments = await self.firestore.list_garments_metadata(user_id=user_id)
        if len(garments) < 5:
            logger.warning(f"User {user_id} has only {len(garments)} garments. Minimum 5 required for feed.")
            return None

        # Fetch weather
        weather_dict = None
        location_str = None
        if user_profile.location:
            city = user_profile.location.city
            weather_info = await self.weather_service.get_weather_by_coords(
                user_profile.location.lat,
                user_profile.location.lon
            )
            if weather_info:
                location_str = city or weather_info.city
                weather_dict = {
                    "temperature": weather_info.temperature,
                    "description": weather_info.description,
                    "condition": weather_info.condition
                }
        if not weather_dict:
            # Fallback mild weather
            weather_dict = {"temperature": 20, "description": "mild", "condition": "clear"}
            location_str = "your location"

        # Fetch user feedback to avoid highly disliked style combinations
        feedback_history = await self.firestore.list_user_feedback(user_id, limit=50)
        disliked_look_ids = {fb.look_id for fb in feedback_history if fb.action == "dislike"}

        # 2. Select Versatile & Underused items
        # Versatile = a top or bottom with high versatility score, or just a neutral staple
        basics = [g for g in garments if g.category in ["top", "bottom"]]
        versatile_item = None
        if basics:
            # Sort by versatility score descending
            basics.sort(key=lambda g: g.recommendation_scores.versatility if g.recommendation_scores else 0.5, reverse=True)
            versatile_item = basics[0]
        else:
            versatile_item = random.choice(garments)

        # Underused = an item that has oldest update time or randomly selected from less active items
        underused_item = None
        non_versatile = [g for g in garments if g.garment_id != versatile_item.garment_id]
        if non_versatile:
            underused_item = random.choice(non_versatile)
        else:
            underused_item = versatile_item

        # 3. Score candidate combinations
        scored_outfits = self.scorer.generate_top_outfits(
            garments=garments,
            user_profile=user_profile,
            weather=weather_dict,
            limit=12
        )
        if not scored_outfits:
            logger.warning("Failed to generate any scored outfits")
            return None

        # Format candidates for Gemini prompt
        candidates_data = []
        for i, scored in enumerate(scored_outfits):
            candidates_data.append({
                "candidate_index": i,
                "garment_ids": scored.garment_ids,
                "overall_score": scored.overall_score,
                "description": [item.description for item in scored.items]
            })

        # Format complete closet details for Gemini to prevent hallucinations
        closet_data = []
        for g in garments:
            closet_data.append({
                "id": g.garment_id,
                "category": g.category,
                "color_family": g.colors.color_family if g.colors else "unknown",
                "dominant_color": g.colors.dominant if g.colors else "unknown",
                "fit_type": g.fit_type or "regular",
                "style_tags": g.description.style_tags if g.description else [],
                "short_description": g.description.short if g.description else "clothing item"
            })

        # 4. Invoke Gemini to curate feed
        client = self._get_gemini_client()
        
        # Build prompt
        profile_desc = f"Undertone: {user_profile.skin_tone.undertone if user_profile.skin_tone else 'neutral'}. Season: {user_profile.skin_tone.season if user_profile.skin_tone else 'all-season'}."
        weather_desc = f"{weather_dict['temperature']}°C, {weather_dict['description']} in {location_str}."

        prompt = f"""You are a high-end fashion editor at Vogue. Your task is to compile a highly personalized daily style magazine feed for a user named Hardik.

Context:
- User Profile: {profile_desc}
- Today's Weather: {weather_desc}

User's Closet (ONLY use garments listed here, do NOT make up garment IDs):
{json.dumps(closet_data, indent=2)}

Top Candidate Outfits (Calculated by style scorer):
{json.dumps(candidates_data, indent=2)}

Versatile Staple Selected for 'One Item, Three Ways': ID: {versatile_item.garment_id} ({versatile_item.description.short if versatile_item.description else "Basic staple"})
Underused Garment Selected for 'The Underused Edit': ID: {underused_item.garment_id} ({underused_item.description.short if underused_item.description else "Unique piece"})

Generate an editorial-style magazine feed in JSON format with the following exact keys:
{{
  "cover_look": {{
    "title": "Featured bold headline title (e.g. 'The Modern Executive Uniform')",
    "subtitle": "Chic subtitle catchphrase",
    "garment_ids": ["array of garment IDs making up the cover look outfit (should be top-scoring candidate)"],
    "hero_item_id": "the primary statement piece ID from the cover look",
    "occasion": "suitable occasion (e.g. 'Creative Workplace')",
    "why_it_works": "1-2 sentence editorial explanation of color/fit harmony in a Vogue editor voice",
    "styling_tips": ["tip 1", "tip 2"],
    "swaps": [
      {{
        "replace_item_id": "item ID in cover look",
        "with_item_id": "an alternative item ID from the closet",
        "reason": "why this alternative swap works (e.g. 'Swap the sneakers for loafers to dress it up')"
      }}
    ],
    "score": 0.95
  }},
  "daily_fits": [
    // Array of exactly 3 LookCard objects representing other daily outfits for today's weather
  ],
  "one_item_three_ways": [
    // Array of exactly 3 LookCard objects styling the Versatile Staple garment (ID: {versatile_item.garment_id}) in 3 different contexts (e.g., Weekend Casual, Date Night, Smart Workplace).
    // The hero_item_id for all three cards MUST be the versatile staple ID: {versatile_item.garment_id}.
  ],
  "underused_edit": {{
    // A single LookCard object built around the underused garment (ID: {underused_item.garment_id}).
    // The hero_item_id MUST be the underused garment ID: {underused_item.garment_id}.
  }}
}}

Guidelines for the Editor's Voice:
- Tone should be witty, confident, opinionated, and highly visual.
- Use descriptors like "clean silhouette," "tonal play," "low visual noise," "effortless structure."
- Ensure all garment IDs used in the outfits exist in the provided Closet data.
- Ensure the outfits are realistic and complete (e.g., top + bottom, or dress, plus optional outerwear).

Return ONLY the raw JSON string."""

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_TEXT_MODEL,
                contents=[prompt],
            )
            
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text.strip()
                                
                                # Clean JSON block
                                if text.startswith("```json"):
                                    text = text[7:]
                                if text.startswith("```"):
                                    text = text[3:]
                                if text.endswith("```"):
                                    text = text[:-3]
                                text = text.strip()
                                
                                data = json.loads(text)
                                
                                # Convert dict data to LookCard / MagazineFeed objects
                                def make_look_card(lc_data, section_name):
                                    # Fallback scores
                                    score = lc_data.get("score", 0.85)
                                    
                                    # Clean up swap suggestions
                                    swaps = []
                                    for s in lc_data.get("swaps", []):
                                        if s.get("replace_item_id") and s.get("with_item_id"):
                                            swaps.append(SwapSuggestion(
                                                replace_item_id=s["replace_item_id"],
                                                with_item_id=s["with_item_id"],
                                                reason=s.get("reason", "Alternative option")
                                            ))
                                            
                                    return LookCard(
                                        id=f"look-{uuid.uuid4().hex[:8]}",
                                        title=lc_data.get("title", "Modern Fit"),
                                        subtitle=lc_data.get("subtitle"),
                                        section=section_name,
                                        garment_ids=lc_data.get("garment_ids", []),
                                        hero_item_id=lc_data.get("hero_item_id"),
                                        occasion=lc_data.get("occasion"),
                                        why_it_works=lc_data.get("why_it_works", "Great pairing"),
                                        styling_tips=lc_data.get("styling_tips", []),
                                        swaps=swaps,
                                        score=score,
                                        generated_at=datetime.utcnow()
                                    )

                                # Structure feed
                                cover_look = make_look_card(data["cover_look"], "cover")
                                daily_fits = [make_look_card(lc, "daily") for lc in data.get("daily_fits", [])[:3]]
                                one_item_three_ways = [make_look_card(lc, "one_item_three_ways") for lc in data.get("one_item_three_ways", [])[:3]]
                                underused_edit = make_look_card(data["underused_edit"], "underused")

                                feed = MagazineFeed(
                                    user_id=user_id,
                                    date=today_str,
                                    cover_look=cover_look,
                                    daily_fits=daily_fits,
                                    one_item_three_ways=one_item_three_ways,
                                    underused_edit=underused_edit,
                                    generated_at=datetime.utcnow()
                                )

                                # Save to Firestore
                                await self.firestore.save_magazine_feed(feed)
                                logger.info(f"Successfully generated and saved magazine feed for {user_id}")
                                return feed
                                
            logger.error("GenAI did not return valid candidate text")
            return None

        except Exception as e:
            logger.error(f"Error compiling magazine feed: {e}", exc_info=True)
            return None

    async def generate_mock_magazine_feed(self, user_id: str) -> MagazineFeed:
        """Generates a high-quality mock editorial feed with public Unsplash assets for previewing the UI."""
        seed_mock_garments(user_id)
            
        today_str = date.today().isoformat()
        
        # Build looks using mock garment IDs
        cover_look = LookCard(
            id="mock-cover",
            title="The Creative Director",
            subtitle="Low Contrast, Maximum Impact",
            section="cover",
            garment_ids=["mock-g1", "mock-g2", "mock-g3"],
            hero_item_id="mock-g1",
            occasion="Creative Workplace",
            why_it_works="The fluid drape of the cream trenchcoat pairs elegantly with a crisp white oxford. The olive chinos anchor the look without adding harsh contrast.",
            styling_tips=[
                "Leave the trenchcoat unbelted to show the layered silhouette.",
                "Sleeve roll the oxford shirt slightly for an effortless air."
            ],
            swaps=[
                SwapSuggestion(
                    replace_item_id="mock-g1",
                    with_item_id="mock-g5",
                    reason="Swap for the denim jacket to make it a casual weekend brunch fit."
                )
            ],
            score=0.96,
            generated_at=datetime.utcnow()
        )
        
        daily_fits = [
            LookCard(
                id="mock-fit-1",
                title="Tonal Casual",
                section="daily",
                garment_ids=["mock-g6", "mock-g7", "mock-g4"],
                why_it_works="Charcoal and black create a sleek, low-noise palette. The addition of brown leather loafers adds a touch of classic polish.",
                occasion="Brunch & City Walk",
                styling_tips=["Opt for no-show socks to keep the ankle clean."],
                score=0.88,
                generated_at=datetime.utcnow()
            ),
            LookCard(
                id="mock-fit-2",
                title="High-Street Layering",
                section="daily",
                garment_ids=["mock-g5", "mock-g2", "mock-g3", "mock-g8"],
                why_it_works="Layering a washed denim jacket over a white oxford button-down adds textured contrast. Chinos and Chelsea boots frame a refined street silhouette.",
                occasion="Casual Friday",
                styling_tips=["Keep only the middle buttons of the denim jacket done."],
                score=0.91,
                generated_at=datetime.utcnow()
            ),
            LookCard(
                id="mock-fit-3",
                title="Monochrome Founder",
                section="daily",
                garment_ids=["mock-g6", "mock-g3", "mock-g8"],
                why_it_works="All-black upper layered elements with cream chinos makes the black contrast pop. Chelsea boots add a solid foundation.",
                occasion="Investor Coffee",
                styling_tips=["Tuck in the black tee for clean waistband lines."],
                score=0.85,
                generated_at=datetime.utcnow()
            )
        ]
        
        one_item_three_ways = [
            LookCard(
                id="mock-oitw-1",
                title="1. Creative Workplace",
                section="one_item_three_ways",
                garment_ids=["mock-g2", "mock-g3", "mock-g4"],
                hero_item_id="mock-g2",
                why_it_works="White oxford button-down styled with olive chinos and loafers. A smart, minimalist profile that commands room confidence.",
                occasion="Gallery Opening",
                score=0.94,
                generated_at=datetime.utcnow()
            ),
            LookCard(
                id="mock-oitw-2",
                title="2. High-Street Layering",
                section="one_item_three_ways",
                garment_ids=["mock-g5", "mock-g2", "mock-g7", "mock-g8"],
                hero_item_id="mock-g2",
                why_it_works="A vintage denim jacket tones down the structure of the oxford shirt. Charcoal trousers and boots ground the look.",
                occasion="Weekend Gallery Walk",
                score=0.89,
                generated_at=datetime.utcnow()
            ),
            LookCard(
                id="mock-oitw-3",
                title="3. Transition Evening",
                section="one_item_three_ways",
                garment_ids=["mock-g1", "mock-g2", "mock-g7", "mock-g4"],
                hero_item_id="mock-g2",
                why_it_works="Dressing up the white shirt with trousers and a trench. Refined loafers make it perfect for dinner dates.",
                occasion="Cocktail Dinner",
                score=0.95,
                generated_at=datetime.utcnow()
            )
        ]
        
        underused_edit = LookCard(
            id="mock-underused",
            title="The Resurrection Fit",
            section="underused",
            garment_ids=["mock-g8", "mock-g6", "mock-g7", "mock-g1"],
            hero_item_id="mock-g8",
            why_it_works="These boots are too good to sit in the closet. We've paired them with charcoal trousers and a black tee, layered with the trenchcoat for a powerful city uniform.",
            occasion="Late Night Coffee Run",
            styling_tips=["Let the hem of the trousers rest slightly over the boot cuffs."],
            score=0.90,
            generated_at=datetime.utcnow()
        )
        
        return MagazineFeed(
            user_id=user_id,
            date=today_str,
            cover_look=cover_look,
            daily_fits=daily_fits,
            one_item_three_ways=one_item_three_ways,
            underused_edit=underused_edit,
            generated_at=datetime.utcnow()
        )


def seed_mock_garments(user_id: str = "dev-admin-user-id"):
    """Seed the mock wardrobe garments in the local in-memory storage dictionary."""
    from app.services.firestore import _memory_garments
    
    mock_items = [
        {
            "garment_id": "mock-g1",
            "category": "outerwear",
            "front_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=500",
            "description": {"short": "Cream Trenchcoat", "detailed": "Cream Trenchcoat", "style_tags": ["classic", "work"]}
        },
        {
            "garment_id": "mock-g2",
            "category": "top",
            "front_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500",
            "description": {"short": "White Oxford Shirt", "detailed": "White Oxford Shirt", "style_tags": ["classic", "minimalist"]}
        },
        {
            "garment_id": "mock-g3",
            "category": "bottom",
            "front_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=500",
            "description": {"short": "Relaxed Chinos", "detailed": "Relaxed Chinos", "style_tags": ["casual", "streetwear"]}
        },
        {
            "garment_id": "mock-g4",
            "category": "shoes",
            "front_url": "https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=500",
            "description": {"short": "Leather Loafers", "detailed": "Leather Loafers", "style_tags": ["classic", "smart-casual"]}
        },
        {
            "garment_id": "mock-g5",
            "category": "outerwear",
            "front_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500",
            "description": {"short": "Denim Jacket", "detailed": "Denim Jacket", "style_tags": ["casual", "vintage"]}
        },
        {
            "garment_id": "mock-g6",
            "category": "top",
            "front_url": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=500",
            "description": {"short": "Black Cotton Tee", "detailed": "Black Cotton Tee", "style_tags": ["casual", "minimalist"]}
        },
        {
            "garment_id": "mock-g7",
            "category": "bottom",
            "front_url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=500",
            "description": {"short": "Charcoal Trousers", "detailed": "Charcoal Trousers", "style_tags": ["formal", "classic"]}
        },
        {
            "garment_id": "mock-g8",
            "category": "shoes",
            "front_url": "https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=500",
            "ghost_mannequin_url": "https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=500",
            "description": {"short": "Leather Chelsea Boots", "detailed": "Leather Chelsea Boots", "style_tags": ["classic", "streetwear"]}
        }
    ]
    
    for item in mock_items:
        item_dict = {
            "id": item["garment_id"],
            "url": item["front_url"],
            "user_id": user_id,
            **item
        }
        _memory_garments[item["garment_id"]] = item_dict


async def async_seed_mock_garments(user_id: str = "dev-admin-user-id", firestore_service=None) -> None:
    """Seed the mock wardrobe garments in the database and local memory."""
    # Seed in-memory
    seed_mock_garments(user_id)
    
    if firestore_service is None:
        return
        
    # Seed to firestore if client is active and configured
    from app.models.garment import GarmentMetadata, GarmentCategory, GarmentDescription, WeatherRange
    from app.services.firestore import _memory_garments
    
    for garment_id, data in _memory_garments.items():
        if data.get("user_id") != user_id:
            continue
        try:
            if firestore_service.client is not None and not firestore_service._use_memory:
                # Check if it already exists in firestore
                existing = await firestore_service.get_garment_metadata(garment_id)
                if not existing or existing.user_id != user_id:
                    metadata = GarmentMetadata(
                        garment_id=garment_id,
                        user_id=user_id,
                        category=GarmentCategory(data["category"]),
                        ghost_mannequin_url=data["front_url"],
                        description=GarmentDescription(
                            short=data["description"]["short"],
                            detailed=data["description"]["detailed"],
                            style_tags=data["description"]["style_tags"]
                        ),
                        weather_range=WeatherRange(min_temp=10, max_temp=30)
                    )
                    await firestore_service.save_garment_metadata(metadata)
        except Exception as e:
            logger.warning(f"Failed to save mock garment {garment_id} to Firestore: {e}")
