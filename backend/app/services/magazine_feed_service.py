"""Magazine Feed Service - curates personalized editorial feeds using Gemini."""

import json
import os
import random
import uuid
from datetime import date, datetime
from typing import Optional

from app.config import get_settings
from app.logging_config import get_logger
from app.models.magazine_feed import LookCard, MagazineFeed, SwapSuggestion
from app.services.firestore import FirestoreService, is_legacy_demo_garment_id
from app.services.outfit_scorer import OutfitScorerService
from app.services.weather import WeatherService

settings = get_settings()
logger = get_logger("magazine_feed_service")


def _contains_legacy_demo_garments(feed: MagazineFeed) -> bool:
    """Return whether a cached issue references the retired demo closet."""
    looks = [
        feed.cover_look,
        *feed.daily_fits,
        *feed.one_item_three_ways,
        feed.underused_edit,
    ]
    for look in looks:
        referenced_ids = [*look.garment_ids, look.hero_item_id]
        for swap in look.swaps:
            referenced_ids.extend([swap.replace_item_id, swap.with_item_id])
        if any(is_legacy_demo_garment_id(item_id) for item_id in referenced_ids):
            return True
    return False


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
        2. Ensure user has at least 10 garments.
        3. Score standard combinations to find top outfit candidates.
        4. Select a versatile garment (for 'One Item, Three Ways') and an underused garment.
        5. Invoke Gemini 2.0 to write Vogue-style copy and structure the final looks.
        6. Save the resulting MagazineFeed to Firestore.
        """
        today_str = date.today().isoformat()
        
        # Check cache unless force requested
        if not force_regenerate:
            cached_feed = await self.firestore.get_magazine_feed(user_id, today_str)
            if cached_feed and not _contains_legacy_demo_garments(cached_feed):
                logger.info(f"Returning cached magazine feed for {user_id} on {today_str}")
                return cached_feed
            if cached_feed:
                logger.warning(
                    f"Ignoring cached magazine feed with retired demo garments for {user_id}"
                )

        logger.info(f"Starting magazine feed generation for user {user_id}...")

        # 1. Fetch dependencies
        user_profile = await self.firestore.get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"No user profile found for {user_id}")
            return None

        # Fetch garments
        garments = await self.firestore.list_garments_metadata(user_id=user_id)
        if len(garments) < 10:
            logger.warning(f"User {user_id} has only {len(garments)} garments. Minimum 10 required for feed.")
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
