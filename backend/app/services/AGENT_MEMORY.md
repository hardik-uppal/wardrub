# Agent Memory — backend/app/services

Last updated: 2026-09-11. Scope: progressive style analysis.

- `style_analysis.py` validates/normalizes original photos, asks Gemini for
  structured evidence across all photos in a submission, and merges stage state.
- Blocking issues override confidence. Threshold 0.7 is an engineering gate,
  not a calibrated probability. Provider errors propagate to persisted retry state.
- `merge_analysis` preserves usable results, other stages, and profile preferences.
- `FirestoreService.apply_style_analysis` uses a transaction against the latest
  user document. Write failures propagate; local fallback requires explicit dev
  auth bypass. `ensure_user_profile` atomically creates a non-inferred default,
  preserves existing profiles, and is used by profile bootstrap and Magazine so
  pre-profile accounts are not blocked. Other older Firestore methods retain their
  existing fallback behavior.
- No new raw photos are saved by Profile analysis. Existing avatar-source storage
  is separate. Never analyze a generated avatar as evidence of the user's body.
- Uses existing `GEMINI_TEXT_MODEL` and Gemini credentials/Vertex configuration.
- Tests: `python -m unittest discover -s backend/tests -p test_style_analysis.py`.
  Mocked functional tests do not establish live model accuracy.
