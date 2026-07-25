"""Local-only developer authentication helpers."""

import time
from typing import Any, Dict, Optional


def decode_dev_auth_token(
    token: str,
    enabled: bool,
) -> Optional[Dict[str, Any]]:
    """Return mock claims only when the explicit local bypass is enabled."""
    if not enabled:
        return None

    if token != "dev-mock-admin-token" and not token.startswith("mock-token-"):
        return None

    uid = (
        token.replace("mock-token-", "", 1)
        if token.startswith("mock-token-")
        else "dev-admin-user-id"
    )
    return {
        "uid": uid,
        "email": "admin@wardrub.test",
        "name": "Dev Admin",
        "picture": "https://lh3.googleusercontent.com/a/default-user=s96-c",
        "auth_time": int(time.time()),
        "user_id": uid,
        "firebase": {
            "identities": {"google.com": ["admin@wardrub.test"]},
            "sign_in_provider": "google.com",
        },
    }
