"""Deterministic, bounded candidate ranking. No network, generation or learned taste."""

import hashlib
import json
from itertools import product

from app.services.outfit_scorer import OutfitScorerService

POLICY_VERSION = "closet-rules-v1"
CATEGORY_ORDER = ("top", "bottom", "dress", "outerwear", "shoes")
SHORTLIST_SIZE = 12
BEAM_SIZE = 96


def eligible(garment, user_id):
    return (garment.user_id == user_id and not garment.garment_id.startswith("mock-")
            and garment.ownership == "owned" and garment.readiness != "laundry")


def canonical_items(items):
    return sorted(items, key=lambda g: (CATEGORY_ORDER.index(g.category), g.garment_id))


def outfit_key(user_id, items):
    payload = [user_id, sorted((g.category, g.garment_id) for g in items)]
    return "outfit-" + hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()[:24]


def valid_outfit(items):
    categories = [g.category for g in items]
    if len(set(g.garment_id for g in items)) != len(items) or len(set(categories)) != len(items):
        return False
    core = set(categories) - {"outerwear", "shoes"}
    return core in ({"top", "bottom"}, {"dress"})


class ClosetRanker:
    def __init__(self):
        self.scorer = OutfitScorerService()

    def score(self, items, profile=None, weather=None):
        # Inter-garment harmony is useful before optional personal color analysis.
        ranking_weather = {**weather, "temperature": weather.get("feels_like", weather["temperature"])} if weather is not None else None
        scored = self.scorer.score_outfit(items, None, ranking_weather)
        weight = 0.60 if weather is None else 1.0
        total = (.35 * scored.color_harmony_score + .25 * scored.style_cohesion_score)
        if weather is not None:
            total += .40 * scored.weather_score
        score = total / weight
        # Explicit profile preferences only; an unexplained click is not a style label.
        preferences = {p.lower() for p in (profile.style_preferences if profile else [])}
        tags = [{t.lower() for t in g.description.style_tags} if g.description else set() for g in items]
        if preferences:
            score += .08 * sum(bool(t & preferences) for t in tags) / len(items)
        if weather is not None:
            temp = ranking_weather["temperature"]
            has_layer = any(g.category == "outerwear" for g in items)
            if temp < 12 and not has_layer or temp > 25 and has_layer:
                score -= .12
        scored.overall_score = max(0.0, min(1.0, score))
        return scored

    def rank(self, garments, user_id, profile=None, weather=None, limit=4):
        available = [g for g in garments if eligible(g, user_id)]
        groups = {}
        for category in CATEGORY_ORDER:
            group = [g for g in available if g.category == category]
            group.sort(key=lambda g: (-self.score([g], profile, weather).overall_score, g.garment_id))
            groups[category] = group[:SHORTLIST_SIZE]
        candidates = [[g] for g in groups["dress"]]
        candidates += [list(pair) for pair in product(groups["top"], groups["bottom"])]

        def best(combinations):
            return sorted(combinations, key=lambda items: (
                -self.score(items, profile, weather).overall_score,
                outfit_key(user_id, items),
            ))[:BEAM_SIZE]

        candidates = best(candidates)
        for category in ("outerwear", "shoes"):
            candidates = best(candidates + [items + [g] for items in candidates for g in groups[category]])
        # Prefer alternatives with a different core outfit before minor layer changes.
        selected, deferred, cores = [], [], set()
        for items in candidates:
            core = tuple(sorted(g.garment_id for g in items if g.category in {"top", "bottom", "dress"}))
            if core in cores:
                deferred.append(items)
            else:
                selected.append(items)
                cores.add(core)
        return [canonical_items(items) for items in (selected + deferred)[:limit]]

    def swap(self, garments, user_id, garment_ids, replace_id, with_id=None, profile=None, weather=None):
        owned = {g.garment_id: g for g in garments if g.user_id == user_id and not g.garment_id.startswith("mock-")}
        if replace_id not in garment_ids or any(gid not in owned for gid in garment_ids):
            raise ValueError("Outfit contains an unknown garment")
        original = [owned[gid] for gid in garment_ids]
        if not valid_outfit(original):
            raise ValueError("Choose a top and bottom, or a dress, with optional layers and shoes")
        locked = [g for g in original if g.garment_id != replace_id]
        if any(not eligible(g, user_id) for g in locked):
            raise ValueError("Another piece is unavailable. Refresh your outfit first")
        replacements = [g for g in owned.values() if eligible(g, user_id)
                        and g.category == owned[replace_id].category and g.garment_id not in garment_ids
                        and (with_id is None or g.garment_id == with_id)]
        replacements.sort(key=lambda g: (-self.score(locked + [g], profile, weather).overall_score, g.garment_id))
        return canonical_items(locked + [replacements[0]]) if replacements else None
