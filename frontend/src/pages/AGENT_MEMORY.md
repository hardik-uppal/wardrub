# Agent Memory — frontend/src/pages

Last updated: 2026-09-13. Scope: Release A daily wardrobe design.

- App routes: Today at `/` and `/daily-outfit`; Items at `/wardrobe`; Outfits at `/looks`; Profile, Capture, CreateAvatar and DressingRoom retain old paths. Login restores a valid internal destination. Legacy MagazineFeed/DailyOutfit sources are unmounted.
- Today freshly reads grounded suggestions on entry/focus/visibility and day rollover. Weather unknown is explicit; failed refresh clears stale suggestions. Explicit local-day plan remains distinct. Stable IDs are combinations, not exposures. Swaps keep other pieces fixed and remain server-validated.
- OutfitPanel owns real save/plan/wear/undo and optional try-on entry. Daily reason choices set aside a combination only for the local day; Profile history can undo. Only explicit style choices provide lasting boosts. No implicit taste learning.
- Home retains search/sort/category and image detail/deletion, adds Shoes/readiness filters, batch laundry/return/undo and optional storage labels. Missing saved-outfit pieces remain disclosed; generated history is independent.
- Outfits separates Saved outfits/Try-ons and retains history favorites/occasion/sort/download/share/delete and load-older. Manual Create a try-on clears the old draft.
- Capture retains bounded gallery queue and camera fallback, moves back-image/cleanup to secondary details, and offers first-outfit/add-more/origin completion choices. It does not implement detected-item confirmation or resumable jobs.
- CreateAvatar generates a candidate with activate=false, shows Use/Keep current, accepts before refreshing avatar and returning to the exact draft. Cancel returns to origin. Full-body and selfie routes remain. Candidates are not a full avatar gallery.
- DressingRoom restores user-keyed session draft, preserves selection through avatar detour/reload and failure, supports single-item or compatible multiple-piece previews, and refreshes generated history after success. Shoes remain explicitly unsupported by the renderer.
- Profile owns avatar/location/preferences/history/account navigation; StyleProfile is a focused optional analysis or recovery subpage. Analysis retains independent stages and selected files after errors; no generated-avatar evidence. Recovery runs only after explicit import.
- WardrobeProvider caches bootstrap profile reads; explicit successful edits supersede older reads. Analysis retry tests await the button enabled state, not the shared Retry available label (important async regression).
- Verify `npm test`, lint/build/static-route checks and mobile/desktop Playwright journeys, including light/dark nine-view accessibility checks. Browser fixtures are synthetic; real cloud/camera/share/generation and task-completion pilot remain unverified.

## One-photo follow-up — 2026-09-13

- Capture now contains shared chrome and GalleryUpload only: one original photo, automatic labels, Done returns to origin. No category/front/back/cleanup flow. Old multi-view endpoints and existing garment back images remain compatible.
- Home puts sort/category/readiness and optional Manage clothes mode in a compact Filters disclosure. Search stays visible; selection appears only in management mode. Readiness/storage badges are hidden, with editing under Manage this piece in detail. Backend eligibility and laundry/undo remain unchanged.
- Today has no routine refresh/location controls; Profile owns them. Daily device location is account/browser opt-in, runs only with granted permission on Today entry/focus/day change, attempts at most once per local day, and preserves saved city on failure. Choosing a city disables automatic location. No server background tracking or weather-cache change.
- Garment detail exposes original-photo fit only when known. See docs/progress/quiet-controls-PROGRESS.md for verification.
