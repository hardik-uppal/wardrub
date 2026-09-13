# One-photo capture progress

Last updated: 2026-09-13. Source: founder feedback and `docs/product/ONE_PHOTO_CAPTURE.md`.

- Base: merged design PR #27, main `148f2b7`.
- Branch: `codex/one-photo-capture`.
- Implemented: unified camera/gallery capture, automatic labels, original-photo fit observations, persistence/reload, partial import outcomes, collapsed filters and reduced Today copy.
- Verification: 101 backend tests, 64 frontend unit tests; 26 mobile/desktop browser tests passed; lint, production build and static-route checks passed. Parsed-response starter2/2 and small24/24 vs baseline20/24; recommender24/24. These do not establish live model accuracy.
- New dependencies/secrets: none. Existing text/image models reused. No deployment or data migration.
- Pending: publish review branch; real camera/consented-photo inference evaluation before making accuracy claims. Inspect existing GitHub permissions rather than assuming that another session's manual push enabled write access here.

Resume by reviewing this existing branch and its screenshots/patch, then publish it with a write-enabled repository connection. Do not reintroduce mandatory category/front/back setup.
