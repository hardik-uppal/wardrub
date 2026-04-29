"""Outfit scoring service for recommendation engine."""

import itertools
from typing import List, Dict, Any, Optional, Tuple

from app.logging_config import get_logger
from app.models.garment import GarmentMetadata, GarmentColors, ColorWarmth
from app.models.user_profile import UserProfile, SkinTone, ColorSeason
from app.models.daily_looks import ScoredOutfit, OutfitItem

logger = get_logger("outfit_scorer")

# Scoring weights
WEIGHT_WEATHER = 0.30
WEIGHT_COLOR = 0.35
WEIGHT_STYLE = 0.20
WEIGHT_VERSATILITY = 0.15


class OutfitScorerService:
    """Service for scoring outfit combinations."""
    
    def __init__(self):
        """Initialize outfit scorer."""
        pass
    
    def score_outfit(
        self,
        items: List[GarmentMetadata],
        user_profile: Optional[UserProfile],
        weather: Optional[Dict[str, Any]]
    ) -> ScoredOutfit:
        """
        Score an outfit combination based on multiple factors.
        
        Args:
            items: List of garments in the outfit
            user_profile: User's profile (skin tone, preferences)
            weather: Current weather data
        
        Returns:
            ScoredOutfit with breakdown
        """
        # Build outfit items
        outfit_items = [
            OutfitItem(
                garment_id=g.garment_id,
                category=g.category if isinstance(g.category, str) else g.category.value,
                image_url=g.ghost_mannequin_url or "",
                description=g.description.short if g.description else None
            )
            for g in items
        ]
        
        # Calculate individual scores
        weather_score, weather_reasoning = self._score_weather(items, weather)
        color_score, color_reasoning = self._score_color_harmony(items, user_profile)
        style_score, style_reasoning = self._score_style_cohesion(items)
        versatility_score = self._score_versatility(items)
        
        # Weighted overall score
        overall = (
            WEIGHT_WEATHER * weather_score +
            WEIGHT_COLOR * color_score +
            WEIGHT_STYLE * style_score +
            WEIGHT_VERSATILITY * versatility_score
        )
        
        return ScoredOutfit(
            garment_ids=[g.garment_id for g in items],
            items=outfit_items,
            weather_score=weather_score,
            color_harmony_score=color_score,
            style_cohesion_score=style_score,
            versatility_score=versatility_score,
            overall_score=overall,
            weather_reasoning=weather_reasoning,
            color_reasoning=color_reasoning,
            style_reasoning=style_reasoning
        )
    
    def _score_weather(
        self,
        items: List[GarmentMetadata],
        weather: Optional[Dict[str, Any]]
    ) -> Tuple[float, str]:
        """
        Score outfit based on weather appropriateness.
        
        Args:
            items: Garments in outfit
            weather: Weather data with 'temperature', 'description', etc.
        
        Returns:
            (score, reasoning)
        """
        if not weather:
            return 0.7, "No weather data available"
        
        temp = weather.get("temperature", 20)
        condition = weather.get("description", "").lower()
        
        # Check each garment's weather range
        scores = []
        reasoning_parts = []
        
        for garment in items:
            min_temp = garment.weather_range.min_temp
            max_temp = garment.weather_range.max_temp
            
            # Score based on temperature fit
            if min_temp <= temp <= max_temp:
                scores.append(1.0)
            elif temp < min_temp:
                # Too cold for this garment
                diff = min_temp - temp
                score = max(0.3, 1.0 - (diff / 20))
                scores.append(score)
                reasoning_parts.append(f"{garment.category} may be too light")
            else:
                # Too hot for this garment
                diff = temp - max_temp
                score = max(0.3, 1.0 - (diff / 20))
                scores.append(score)
                reasoning_parts.append(f"{garment.category} may be too warm")
        
        # Check for rain/snow
        if "rain" in condition or "drizzle" in condition:
            has_outerwear = any(
                (g.category if isinstance(g.category, str) else g.category.value) == "outerwear"
                for g in items
            )
            if not has_outerwear:
                reasoning_parts.append("Consider adding a jacket for rain")
        
        avg_score = sum(scores) / len(scores) if scores else 0.7
        
        if not reasoning_parts:
            reasoning = f"Good for {temp}°C weather"
        else:
            reasoning = "; ".join(reasoning_parts)
        
        return avg_score, reasoning
    
    def _score_color_harmony(
        self,
        items: List[GarmentMetadata],
        user_profile: Optional[UserProfile]
    ) -> Tuple[float, str]:
        """
        Score outfit based on color harmony.
        
        Considers:
        - User's skin tone / color season
        - Inter-garment color compatibility
        
        Args:
            items: Garments in outfit
            user_profile: User profile with skin tone
        
        Returns:
            (score, reasoning)
        """
        scores = []
        reasoning_parts = []
        
        # 1. Score against user's color season
        if user_profile and user_profile.skin_tone:
            season = user_profile.skin_tone.season
            undertone = user_profile.skin_tone.undertone
            
            season_str = season if isinstance(season, str) else season.value
            undertone_str = undertone if isinstance(undertone, str) else undertone.value
            
            # Clean up season string if it contains enum prefix
            if "." in season_str:
                season_str = season_str.split(".")[-1].lower()
            season_str = season_str.lower()
            
            # Clean up undertone string
            if "." in undertone_str:
                undertone_str = undertone_str.split(".")[-1].lower()
            undertone_str = undertone_str.lower()
            
            for garment in items:
                if garment.colors:
                    warmth = garment.colors.warmth
                    warmth_str = warmth if isinstance(warmth, str) else warmth.value
                    if "." in warmth_str:
                        warmth_str = warmth_str.split(".")[-1].lower()
                    warmth_str = warmth_str.lower()
                    
                    # Match warmth to undertone
                    if undertone_str == warmth_str:
                        scores.append(1.0)
                    elif warmth_str == "neutral":
                        scores.append(0.85)
                    elif undertone_str == "neutral":
                        scores.append(0.8)
                    else:
                        scores.append(0.5)
            
            # Capitalize season for display
            season_display = season_str.capitalize()
            if season_str in ["spring", "autumn"]:
                reasoning_parts.append(f"Warm tones suit your {season_display} palette")
            else:
                reasoning_parts.append(f"Cool tones complement your {season_display} palette")
        
        # 2. Inter-garment harmony
        colors_info = [g.colors for g in items if g.colors]
        if len(colors_info) >= 2:
            harmony_score = self._calculate_inter_garment_harmony(colors_info)
            scores.append(harmony_score)
            
            if harmony_score >= 0.8:
                reasoning_parts.append("Colors work well together")
            elif harmony_score < 0.5:
                reasoning_parts.append("Color combination may clash")
        
        avg_score = sum(scores) / len(scores) if scores else 0.6
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Color analysis limited"
        
        return avg_score, reasoning
    
    def _calculate_inter_garment_harmony(
        self,
        colors_list: List[GarmentColors]
    ) -> float:
        """
        Calculate color harmony between garments.
        
        Simple heuristics:
        - Same warmth = good
        - Neutral + anything = good
        - Complementary families = good
        - Clashing colors = bad
        """
        if len(colors_list) < 2:
            return 0.7
        
        scores = []
        
        for i, c1 in enumerate(colors_list):
            for c2 in colors_list[i+1:]:
                warmth1 = c1.warmth if isinstance(c1.warmth, str) else c1.warmth.value
                warmth2 = c2.warmth if isinstance(c2.warmth, str) else c2.warmth.value
                
                # Warmth compatibility
                if warmth1 == warmth2:
                    scores.append(1.0)
                elif "neutral" in [warmth1, warmth2]:
                    scores.append(0.9)
                else:
                    scores.append(0.5)
                
                # Color family compatibility
                family1 = c1.color_family.lower()
                family2 = c2.color_family.lower()
                
                # Neutral colors go with everything
                neutrals = ["black", "white", "gray", "beige", "navy"]
                if family1 in neutrals or family2 in neutrals:
                    scores.append(1.0)
                elif family1 == family2:
                    # Same family - could be good (tonal) or boring
                    scores.append(0.8)
                else:
                    # Different families - assume okay
                    scores.append(0.7)
        
        return sum(scores) / len(scores) if scores else 0.7
    
    def _score_style_cohesion(
        self,
        items: List[GarmentMetadata]
    ) -> Tuple[float, str]:
        """
        Score outfit based on style tag overlap.
        
        Args:
            items: Garments in outfit
        
        Returns:
            (score, reasoning)
        """
        # Collect all style tags
        all_tags = []
        for garment in items:
            if garment.description and garment.description.style_tags:
                all_tags.extend(garment.description.style_tags)
        
        if not all_tags:
            return 0.6, "Style analysis limited"
        
        # Find common tags
        tag_counts = {}
        for tag in all_tags:
            tag_lower = tag.lower()
            tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1
        
        # Calculate cohesion based on shared tags
        num_items = len(items)
        shared_tags = [tag for tag, count in tag_counts.items() if count >= 2]
        
        if shared_tags:
            # More shared tags = better cohesion
            cohesion_score = min(1.0, 0.6 + (len(shared_tags) * 0.15))
            style_desc = shared_tags[0].capitalize()
            reasoning = f"{style_desc} style outfit"
        else:
            cohesion_score = 0.5
            reasoning = "Mixed style combination"
        
        # Penalize conflicting styles
        conflicting_pairs = [
            ("formal", "sporty"),
            ("formal", "streetwear"),
            ("vintage", "minimalist"),
            ("bohemian", "preppy")
        ]
        
        tags_lower = set(t.lower() for t in all_tags)
        for s1, s2 in conflicting_pairs:
            if s1 in tags_lower and s2 in tags_lower:
                cohesion_score *= 0.7
                reasoning += " (mixed formality)"
                break
        
        return cohesion_score, reasoning
    
    def _score_versatility(
        self,
        items: List[GarmentMetadata]
    ) -> float:
        """
        Score based on garment versatility scores.
        
        Args:
            items: Garments in outfit
        
        Returns:
            Average versatility score
        """
        scores = []
        for garment in items:
            if garment.recommendation_scores:
                scores.append(garment.recommendation_scores.versatility)
            else:
                scores.append(0.5)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def generate_top_outfits(
        self,
        garments: List[GarmentMetadata],
        user_profile: Optional[UserProfile],
        weather: Optional[Dict[str, Any]],
        limit: int = 3
    ) -> List[ScoredOutfit]:
        """
        Generate top scoring outfit combinations.
        
        Args:
            garments: All available garments
            user_profile: User profile
            weather: Current weather
            limit: Number of outfits to return
        
        Returns:
            List of top ScoredOutfits
        """
        logger.info(f"Generating top {limit} outfits from {len(garments)} garments...")
        
        # Group garments by category
        by_category: Dict[str, List[GarmentMetadata]] = {}
        for g in garments:
            cat = g.category if isinstance(g.category, str) else g.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(g)
        
        logger.info(f"Categories: {list(by_category.keys())}")
        
        # Generate outfit combinations
        combinations = []
        
        # Option 1: Top + Bottom
        tops = by_category.get("top", [])
        bottoms = by_category.get("bottom", [])
        if tops and bottoms:
            for top in tops[:5]:  # Limit to top 5 of each
                for bottom in bottoms[:5]:
                    combinations.append([top, bottom])
        
        # Option 2: Dress alone
        dresses = by_category.get("dress", [])
        for dress in dresses[:3]:
            combinations.append([dress])
        
        # Option 3: Top + Bottom + Outerwear
        outerwear = by_category.get("outerwear", [])
        if tops and bottoms and outerwear:
            for top in tops[:3]:
                for bottom in bottoms[:3]:
                    for outer in outerwear[:3]:
                        combinations.append([top, bottom, outer])
        
        # Option 4: Dress + Outerwear
        if dresses and outerwear:
            for dress in dresses[:3]:
                for outer in outerwear[:3]:
                    combinations.append([dress, outer])
        
        logger.info(f"Generated {len(combinations)} possible combinations")
        
        if not combinations:
            logger.warning("No valid outfit combinations possible")
            return []
        
        # Score all combinations
        scored = []
        for combo in combinations:
            scored_outfit = self.score_outfit(combo, user_profile, weather)
            scored.append(scored_outfit)
        
        # Sort by overall score and return top
        scored.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Ensure diversity - don't return very similar outfits
        diverse_results = []
        used_ids = set()
        
        for outfit in scored:
            # Check if this outfit shares more than half items with existing
            outfit_ids = set(outfit.garment_ids)
            is_too_similar = False
            
            for existing_ids in [set(o.garment_ids) for o in diverse_results]:
                overlap = len(outfit_ids & existing_ids)
                if overlap > len(outfit_ids) / 2:
                    is_too_similar = True
                    break
            
            if not is_too_similar:
                diverse_results.append(outfit)
                if len(diverse_results) >= limit:
                    break
        
        # If we don't have enough diverse results, fill with top scoring
        while len(diverse_results) < limit and len(diverse_results) < len(scored):
            for outfit in scored:
                if outfit not in diverse_results:
                    diverse_results.append(outfit)
                    break
            if len(diverse_results) >= limit:
                break
        
        logger.info(f"Selected {len(diverse_results)} diverse top outfits")
        return diverse_results

