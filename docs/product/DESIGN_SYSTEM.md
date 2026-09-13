# Wardrub daily wardrobe design system

Implemented for the Release A review branch on 2026-09-13. The original flow audit remains a historical before/after register in `USER_FLOWS_CURRENT_AND_PROPOSED.md`.

## Product intent

Take the effort out of choosing, finding and caring for clothes. A useful outfit comes from the user's owned wardrobe and confirmed availability; image generation is optional. Capture starts small, and avatar and style analysis are introduced where they help.

## Navigation and hierarchy

- Today (`/`, legacy `/daily-outfit`): a current suggestion or explicit daily plan, weather context, primary plan/wear action, save, piece swaps and optional try-on. Explanations and corrections expand on demand.
- Wardrobe Items (`/wardrobe`): one Add action, search/sort/category/readiness filters, garment grid, details and batch management.
- Wardrobe Outfits (`/looks`): saved combinations and generated try-ons, with labeled views. Create a try-on retains the manual dressing room (`/dressing-room`).
- Profile (`/profile`): avatar, location, explicit preferences, history, optional style guidance, recovery and sign-out. Color/fit guidance and recovery have focused subpages.
- Add clothes (`/capture`) and avatar creation (`/create-avatar`) retain old URLs and camera/gallery capabilities. Login restores a valid internal destination.

## Visual roles

The implementation source is `frontend/src/index.css`. Legacy glass variables remain compatibility aliases; new screens use quiet surfaces and borders.

| Role | Light | Dark |
|---|---|---|
| Page | #ffffff | #191c19 |
| Secondary surface | #f3f4ee | #272d26 |
| Main text | #242b25 | #f2f3ed |
| Supporting text | #626b61 | #b6c0b3 |
| Action | #304634 | #d9e6d1 |
| Border | #dde2d8 | #434d40 |

Use the existing serif heading / sans-serif UI pairing. Page titles are 32 px desktop, 28 px mobile; supporting copy is 13–14 px. Spacing uses 8/12/16/20/24/32 px increments. Page gutters are 24 px desktop and 20 px mobile, with an 1100 px content cap. Corners use 8/12 px. Primary controls have at least 44 px height. Mobile uses two bottom destinations; desktop uses a 216 px sidebar. Respect system dark mode and reduced motion.

## Shared components

| Component | Responsibility |
|---|---|
| PageHeader / WardrobeTabs | Consistent title, profile/back actions and Items/Outfits navigation |
| OutfitPanel | Garment collage and identity; real save/plan/wear/undo actions; optional preview |
| Dialog | Native modal with keyboard dismissal, focus behavior and labeled heading |
| ResilientImage / UploadPreview | Preserve the record and recover gracefully from image/format failures |
| GalleryUpload | Bounded queue, per-photo outcomes, explicit retries and retained successes |
| StyleAnalysisProgress | Independent colors/fit progress and retained results after failed retries |

Primary actions change with state: Plan for today → I wore this → Undo wear. Save outfit always means a persisted clothing combination; Download always exports an image. A generated image is not evidence of ownership, wear or physical fit.

## State contracts

- Empty, loading, missing image, no match, unavailable weather and failed reads are distinct. Failed Today refresh clears the stale suggestion; an explicit plan remains a plan.
- Clothing availability is unknown / ready / laundry. Wear never automatically changes it. Batch changes are versioned and undoable; a stale write conflicts.
- Library actions require an operation ID and expected version. Success is shown only after the server confirms. Uncertain writes refresh state; they are not blindly replayed.
- Plan/wear and temporary corrections use the browser's local calendar day. The feed date remains explicitly UTC. Corrections expire from ranking on the next local day and can be undone from history.
- Temporary comfort/occasion/style corrections set aside that combination for the day. Only the editable style choices supply lasting preference boosts. No implicit taste learning or exposure-training claims.
- Candidate avatar generation preserves the active avatar until acceptance. The input outfit persists through the detour/reload in user-keyed session storage. Generation failure preserves selection.
- Saved outfits reference garment IDs; missing clothes are disclosed. Generated results retain their own history, garment IDs/categories and avatar revision. Historical images do not change when the avatar is updated.

## Persistence and rollout limits

`closet_libraries` is a Firestore aggregate keyed by a SHA-256 user ID. It is bounded to 200 saved combinations, 365 daily entries, 100 corrections, 2000 location labels and 30 replay receipts; limits produce actionable errors, not silent eviction of history. Split collections before increasing these caps. Local file persistence is permitted only in explicit development bypass; production storage failures fail closed.

The branch uses the existing deployment and services. No automatic migration, new secrets or real image generation is required to review it. The proposed pilot still needs real test accounts, camera/share behavior on supported devices, cloud persistence verification and task-completion/latency measurements before broad rollout. Browser results use synthetic fixtures, not a taste-quality study.

## Deferred work

Shop, social imports, editable ingestion classification/duplicate review, autonomous clothing tracking, learned taste/exposure pipelines, durable background generation jobs and a full avatar-version gallery remain separate work. Candidate cleanup and scalable history storage also need lifecycle policies. This is the core Release A implementation, not evidence that the pilot or future milestones are complete.
