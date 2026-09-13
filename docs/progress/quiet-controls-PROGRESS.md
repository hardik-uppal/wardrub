# Quieter controls — 2026-09-13

Follow-up on `codex/one-photo-capture`, PR #28.

- Today and outfit items no longer display readiness badges, storage labels, routine Refresh or Location controls. Weather remains a short contextual line when available. Error-specific retry actions remain accessible.
- Wardrobe keeps search and a compact Filters disclosure. Sort, category, readiness filtering and optional Manage clothes mode are inside it. Selection checkboxes appear only in management mode. Garment detail hides readiness/storage editing behind Manage this piece.
- Backend readiness persistence, eligibility, version-checked batch updates and laundry undo are unchanged. No automatic clean/laundry inference has been introduced.
- Profile owns manual refresh and location. Use current location explicitly opts this account/browser into a daily device-location attempt on Today entry/focus/day rollover, only with already-granted browser permission. Attempts, including failures, are limited to once per local day; failures preserve saved location. Manual city selection or Stop daily location updates disables automatic attempts. This is browser-local scheduling, not a background/server task or cross-device daily quota. Weather service caching is unchanged.
- Nano Banana / model configuration unchanged.

Verification: 69 frontend unit tests, 28 mobile/desktop browser tests, ESLint, build and static-route checks passed. Browser tests include hidden controls, Profile refresh, expanded-filter overflow and the existing durable laundry/undo loop. Fixed expanded-filter min-content overflow discovered by mobile interaction testing. Tests use synthetic data; real device permission/camera and cloud persistence remain unverified. Backend unchanged in this follow-up; backend tests not rerun.

No merge or deployment performed by this follow-up.
