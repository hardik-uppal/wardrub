# Issue #7 — actual edition and daily freshness

Baseline `62742f5`; branch `fix/feed-edition-date`.

## Edition rule

Calendar-derived **UTC daily edition**, labelled from returned `feed.date` with
month/day/year, not an invented per-user issue number. Forced same-day generation
remains the same dated edition. Missing/invalid dates explicitly say unavailable;
never substitute the browser's current date for potentially older content.

Backend cache date is explicitly UTC, matching Cloud Run's existing usual clock.
No new Firestore counter, migration, model or schedule is introduced.

## Open-tab behavior

Visible tabs check once a minute and when focus/visibility returns. An older dated
feed triggers a normal GET (reusing the server cache if another session generated
it), not forced regeneration. One automatic attempt per UTC day per mounted page;
no retry loop on failure. Hidden tabs do not initiate generation. Timers/listeners
are removed on unmount. An in-flight guard prevents duplicate concurrent calls from
this page, including StrictMode mount effects or repeated refresh clicks. This is
not a cross-process/server-side generation lock.

## Evidence

- Before: literal ISSUE NO. 01 and browser-today date regardless of actual feed.
- After: deterministic component/browser assertions display the returned date.
- Mocked backend with the same 10 garments: initial generation = 1 provider call;
  same-day repeat stays at 1; next UTC day = 2; forced same-day refresh = 3; a second
  user = 4; returning to the first user's cache stays at 4. Old-day cache unchanged.
- Tests compare feed dates and look IDs. Reused garment combinations are legitimate;
  this does not prove new outfit diversity or reproduce a live account content bug.
- Frontend covers daily rollover, focus/visibility, hidden tabs, no automatic failure
  retry, explicit POST refresh, invalid dates and timer cleanup.
- 54 backend tests, 56 frontend tests, 10 browser checks pass. Lint/build/build smoke pass.
- No production photos, model calls or user data changes used for verification.

Location-dependent invalidation and honest weather fallback remain separate #11.
