# Agent Memory — frontend/src/pages

Last updated: 2026-09-11. Scope: Profile style analysis.

- `Profile.jsx` consumes shared `userProfile`; pending analysis completed after
  navigation updates the page and its recommendation requests.
- Explicit uploads support automatic pending-stage analysis and focused color/fit
  retries. Files stay selected on provider failure; saved results remain visible.
- Original analysis photos are sent to AI but not retained by this upload endpoint.
- Recommendation fetch effects cancel stale UI updates when profile data changes.
- `analysis` query parameter is the focus used by onboarding widget links.
- Profile mount uses the shared cached bootstrap read; successful location edits or
  legacy migration request an explicit fresh read that supersedes older requests.
- Profile retry tests must await the button becoming enabled, not just the shared
  “Retry available” label: shared state can update before the request promise and
  caller's finally complete. A deferred mock covers pending/settled states and
  confirms the retained file can actually be resubmitted (post-merge CI race).
- Verify `Profile.test.jsx` plus mobile/desktop `e2e/style-analysis.spec.js`.
