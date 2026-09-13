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
- Magazine masthead uses returned `feed.date`, labelled as a UTC daily edition;
  no permanent issue number or browser-current-date substitution. Missing/invalid
  dates are explicit. Forced same-day refresh remains the same calendar edition.
- Visible Magazine tabs check UTC rollover every minute and on focus/visibility;
  at most one automatic GET per new day, no forced generation or automatic failure
  retry. In-flight reads/refreshes are guarded; listeners/timer cleaned up on unmount.
  Tests: `MagazineFeed.test.jsx`, `magazineEdition.test.js`, core browser journey.

## Recommender foundation — 2026-09-13

- Magazine keeps its routes/layout and UTC edition handling. Foundation feeds may
  have no cover; show an actionable no-outfit state and keep readiness controls.
  Weather unavailable/no-location is explicit. Scores say Suggested combination,
  never calibrated match labels. Returning to a foundation tab refreshes context.
- Cover suggestions and modal Swap buttons call authenticated `/outfits/swap`.
  Replace only the selected outfit on success; keep it on no-alternative/conflict.
  A new ID separates prior try-on output from the changed garment set.
- Readiness mutation refresh clears current suggestions but retains the panel so
  its versioned Undo remains reachable. Refresh/swap and readiness writes cannot
  overlap through the UI. Feedback failures now display instead of only logging.
- Release review adds an explicit stale-suggestions warning and retry when a
  feed refresh fails after data has already loaded; failure cannot remain silent.
- Existing try-on routes/history retained. Shoes remain outfit items but are
  explicitly excluded from the unsupported renderer; current generated previews
  survive same-outfit feed refresh in component memory.
- Browser: `e2e/recommender.spec.js` covers swap/laundry/undo/empty state at mobile
  and desktop sizes with API fixtures, accessibility and overflow checks.
