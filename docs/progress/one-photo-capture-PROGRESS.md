# One-photo capture progress

Last updated: 2026-09-13. Source: founder feedback and `docs/product/ONE_PHOTO_CAPTURE.md`.

- Base: merged design PR #27, main `148f2b7`.
- Branch: `codex/one-photo-capture`; published in [draft PR #28](https://github.com/hardik-uppal/wardrub/pull/28).
- Published implementation commits: `ac9a84a` (one-photo capture), `52d594e` (quieter controls and opt-in daily location). All three PR checks passed for `52d594e`.
- Implemented: unified camera/gallery capture, automatic labels, original-photo fit observations, persistence/reload, partial import outcomes, collapsed filters and reduced Today copy.
- Verification: 101 backend tests, 64 frontend unit tests; 26 mobile/desktop browser tests passed; lint, production build and static-route checks passed. Parsed-response starter2/2 and small24/24 vs baseline20/24; recommender24/24. These do not establish live model accuracy.
- New dependencies/secrets: none. Existing text/image models reused. No deployment or data migration.
- Quieter-controls follow-up: readiness/storage badges removed; Filters contains optional management; Profile owns location and refresh. Backend readiness and model selection are unchanged. See [follow-up ledger](quiet-controls-PROGRESS.md).
- Fresh follow-up verification: 69 frontend unit tests, 28 mobile/desktop browser tests, lint/build/static-route checks passed. The 101 backend tests and parsed-response benchmarks above were recorded for the original capture change, not rerun for this frontend-only follow-up.
- Previous GitHub 403 publishing blocker resolved using the existing authenticated repository-owner account. No credentials were added to the repository.
- Pending: PR review/merge authorization and real camera/consented-photo inference evaluation. PR #28 is not merged or deployed.

Resume with PR #28 and the quieter-controls ledger. Do not restart or republish the existing implementation, reintroduce mandatory category/front/back setup, or treat synthetic tests as real-photo accuracy evidence.
