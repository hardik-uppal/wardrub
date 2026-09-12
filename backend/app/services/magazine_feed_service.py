"""Grounded daily outfits; editorial/image generation is outside the ranking path."""

import hashlib
import json
from datetime import datetime, timezone

from app.models.magazine_feed import LookCard, MagazineFeed, SwapSuggestion
from app.services.firestore import FirestoreService
from app.services.closet_ranker import ClosetRanker, POLICY_VERSION, outfit_key
from app.services.weather import WeatherService


class MagazineFeedService:
    def __init__(self):
        self.firestore = FirestoreService()
        self.weather_service = WeatherService()
        self.ranker = ClosetRanker()

    async def context(self, user_id):
        profile = await self.firestore.ensure_user_profile(user_id)
        garments = await self.firestore.list_garments_metadata(user_id=user_id, limit=None, strict=True)
        weather, status = None, "no_location"
        if profile.location:
            observation = await self.weather_service.get_cached_weather_by_coords(profile.location.lat, profile.location.lon)
            status = "available" if observation else "unavailable"
            if observation:
                weather = observation.model_dump(mode="json")
        return profile, garments, weather, status

    def look(self, user_id, items, garments, profile, weather, section="daily"):
        scored = self.ranker.score(items, profile, weather)
        reasons = ["A combination from your wardrobe."]
        if weather:
            known_ranges = [g for g in items if (g.weather_range.min_temp, g.weather_range.max_temp) != (0, 40)]
            if known_ranges:
                reasons.append(f"Compared with available garment temperature estimates for {weather.get('feels_like', weather['temperature']):g}°C feels-like weather.")
            if len(known_ranges) != len(items):
                reasons.append("Some garment warmth information is unknown; check your comfort.")
        else:
            reasons.append("Weather is unknown; check the conditions before dressing.")
        unknown = [g.garment_id for g in items if g.readiness == "unknown"]
        reasons.append("Check that these pieces are ready to wear." if unknown else "All pieces are marked ready to wear.")
        if not any(g.category == "shoes" for g in items):
            reasons.append("Choose your shoes separately.")
        swaps = []
        for item in items:
            replacement = self.ranker.swap(garments, user_id, [g.garment_id for g in items], item.garment_id,
                                           profile=profile, weather=weather)
            if replacement:
                new_id = next(g.garment_id for g in replacement if g.garment_id not in {i.garment_id for i in items})
                swaps.append(SwapSuggestion(replace_item_id=item.garment_id, with_item_id=new_id,
                                            reason=f"Change the {item.category}; keep the other pieces."))
        return LookCard(id=outfit_key(user_id, items), title=" + ".join(g.category.capitalize() for g in items),
                        section=section, garment_ids=[g.garment_id for g in items],
                        hero_item_id=items[0].garment_id, why_it_works=" ".join(reasons),
                        swaps=swaps, score=scored.overall_score, unknown_readiness_ids=unknown,
                        policy_version=POLICY_VERSION)

    async def generate_magazine_feed(self, user_id: str, force_regenerate: bool = False) -> MagazineFeed:
        # Re-read wardrobe/profile on every request. Old daily editorial caches cannot
        # override current ownership/readiness. Cheap ranking needs no inference cache.
        profile, garments, weather, status = await self.context(user_id)
        candidates = self.ranker.rank(garments, user_id, profile, weather)
        looks = [self.look(user_id, items, garments, profile, weather, "cover" if i == 0 else "daily")
                 for i, items in enumerate(candidates)]
        version = hashlib.sha256(json.dumps([
            (g.garment_id, g.ownership, g.readiness, g.readiness_version, g.updated_at.isoformat())
            for g in sorted(garments, key=lambda g: g.garment_id)
        ], separators=(",", ":")).encode()).hexdigest()[:24]
        return MagazineFeed(user_id=user_id, date=datetime.now(timezone.utc).date().isoformat(),
                            cover_look=looks[0] if looks else None, daily_fits=looks[1:],
                            weather=weather, weather_status=status, policy_version=POLICY_VERSION,
                            wardrobe_version=version)

    async def swap(self, user_id, request):
        profile, garments, weather, status = await self.context(user_id)
        items = self.ranker.swap(garments, user_id, request.garment_ids, request.replace_item_id,
                                 request.with_item_id, profile, weather)
        return self.look(user_id, items, garments, profile, weather) if items else None
