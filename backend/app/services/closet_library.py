"""User-scoped, versioned outfit library. No image generation or implicit wear."""

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from threading import Lock

from app.services.firestore import FirestoreService, settings
from app.services.closet_ranker import outfit_key, valid_outfit

_lock = Lock()
LOCAL_DIR = Path(__file__).resolve().parents[2] / "logs" / "closet_libraries"


def empty_library():
    return {
        "version": 0,
        "outfits": {},
        "days": {},
        "locations": {},
        "styles": [],
        "operations": {},
        "feedback": {},
    }


def apply_action(current, request, garments, user_id):
    """Pure reducer; version/operation checks prevent stale writes and duplicate actions."""
    state = deepcopy(current or empty_library())
    state.setdefault("feedback", {})
    payload = request.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    receipt = state["operations"].get(request.operation_id)
    if receipt:
        if receipt != digest:
            raise ValueError(
                "This action identifier was already used. Refresh and try again."
            )
        return state
    if request.expected_version != state["version"]:
        raise ValueError("Your closet changed elsewhere. Refresh before trying again.")
    now = datetime.now(timezone.utc).isoformat()
    ids = request.garment_ids
    owned = {
        g.garment_id: g
        for g in garments
        if g.user_id == user_id
        and g.ownership == "owned"
        and not g.garment_id.startswith("mock-")
    }
    if request.action in {"save", "plan", "wore", "location", "feedback"}:
        if not ids or any(gid not in owned for gid in ids) or len(ids) != len(set(ids)):
            raise LookupError(
                "Some clothes are missing from your wardrobe. Refresh first."
            )
    if request.action in {"save", "plan", "wore"}:
        items = [owned[gid] for gid in ids]
        if not valid_outfit(items):
            raise ValueError(
                "Choose a top and bottom, or a dress, with optional layers and shoes."
            )
        if request.action in {"plan", "wore"} and any(
            g.readiness == "laundry" for g in items
        ):
            raise ValueError(
                "A piece is in laundry. Update readiness or choose another outfit."
            )
        outfit = {
            "id": outfit_key(user_id, items),
            "garment_ids": ids,
            "title": request.title or "My outfit",
            "created_at": now,
        }
        if request.action == "save":
            if len(state["outfits"]) >= 200 and outfit["id"] not in state["outfits"]:
                raise ValueError(
                    "Your library holds 200 outfits. Remove one before saving another."
                )
            state["outfits"].setdefault(outfit["id"], outfit)
        else:
            day = request.day.isoformat() if request.day else None
            if not day:
                raise ValueError("Choose a date for this outfit.")
            previous = state["days"].get(day)
            if (
                previous
                and previous.get("worn")
                and (previous["id"] != outfit["id"] or request.action == "plan")
            ):
                raise ValueError(
                    "Undo the confirmed wear before replacing this day’s outfit."
                )
            state["days"][day] = {
                **outfit,
                "worn": request.action == "wore",
                "worn_at": now if request.action == "wore" else None,
            }
            # Bound this small daily-intent document, without silently discarding history.
            if len(state["days"]) > 365:
                raise ValueError(
                    "Your daily log is full. Remove an old entry before adding a new date."
                )
    elif request.action == "delete":
        state["outfits"].pop(request.outfit_id, None)
    elif request.action in {"unplan", "unwear"}:
        day = request.day.isoformat() if request.day else ""
        record = state["days"].get(day)
        if not record or record["id"] != request.outfit_id:
            raise ValueError("This day has changed. Refresh before undoing.")
        if request.action == "unwear":
            record["worn"], record["worn_at"] = False, None
        elif record.get("worn"):
            raise ValueError("Undo wear before removing the plan.")
        else:
            del state["days"][day]
    elif request.action == "feedback":
        items = [owned[gid] for gid in ids]
        if not valid_outfit(items) or not request.day:
            raise ValueError("Choose a complete outfit and a date for this correction.")
        if len(state["feedback"]) >= 100:
            raise ValueError("Remove an older correction before adding another.")
        state["feedback"][request.operation_id] = {
            "id": request.operation_id,
            "outfit_id": outfit_key(user_id, items),
            "garment_ids": ids,
            "day": request.day.isoformat(),
            "reason": request.reason,
            "policy_version": request.policy_version,
            "created_at": now,
        }
    elif request.action == "undo_feedback":
        state["feedback"].pop(request.outfit_id, None)
    elif request.action == "location":
        for gid in ids:
            if request.location.strip():
                state["locations"][gid] = request.location.strip()
            else:
                state["locations"].pop(gid, None)
    elif request.action == "styles":
        state["styles_set"] = True
        state["styles"] = sorted(
            set(s.strip().lower() for s in request.styles if s.strip())
        )
    if len(state["locations"]) > 2000:
        raise ValueError(
            "Location storage is full. Clear an old label before adding another."
        )
    state["version"] += 1
    state["operations"][request.operation_id] = digest
    state["operations"] = dict(list(state["operations"].items())[-30:])
    return state


class ClosetLibrary:
    def __init__(self):
        self.firestore = FirestoreService()

    def _local_path(self, user_id):
        return LOCAL_DIR / (hashlib.sha256(user_id.encode()).hexdigest() + ".json")

    def _local_read(self, user_id):
        if not settings.ALLOW_DEV_AUTH_BYPASS:
            raise RuntimeError("Closet storage is unavailable.")
        path = self._local_path(user_id)
        return json.loads(path.read_text()) if path.exists() else empty_library()

    async def read(self, user_id):
        def load():
            client = self.firestore.client
            if client is None:
                with _lock:
                    return self._local_read(user_id)
            ref = client.collection("closet_libraries").document(
                hashlib.sha256(user_id.encode()).hexdigest()
            )
            snap = ref.get()
            return snap.to_dict() if snap.exists else empty_library()

        return await asyncio.to_thread(load)

    async def mutate(self, user_id, request):
        # A strict wardrobe read fails closed on missing production dependencies.
        garments = await self.firestore.list_garments_metadata(
            user_id, limit=None, strict=True
        )

        def save():
            client = self.firestore.client
            if client is None:
                with _lock:
                    updated = apply_action(
                        self._local_read(user_id), request, garments, user_id
                    )
                    path = self._local_path(user_id)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(updated))
                    os.replace(tmp, path)
                    return updated
            from google.cloud import firestore

            ref = client.collection("closet_libraries").document(
                hashlib.sha256(user_id.encode()).hexdigest()
            )

            @firestore.transactional
            def update(transaction):
                snap = ref.get(transaction=transaction)
                # Recheck referenced clothes in the transaction, including readiness.
                current_garments = []
                from app.models.garment import GarmentMetadata

                for gid in request.garment_ids:
                    garment = (
                        client.collection("garments")
                        .document(gid)
                        .get(transaction=transaction)
                    )
                    if garment.exists:
                        current_garments.append(GarmentMetadata(**garment.to_dict()))
                updated = apply_action(
                    snap.to_dict() if snap.exists else None,
                    request,
                    current_garments,
                    user_id,
                )
                transaction.set(ref, updated)
                return updated

            return update(client.transaction())

        return await asyncio.to_thread(save)
