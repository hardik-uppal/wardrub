# Agent Memory — frontend/src/components

Last updated: 2026-09-11. Scope: style analysis guidance.

- `StyleAnalysisProgress.jsx` shows independent colors/fit state, backend photo
  requests, retained results after retries, and a pause suggestion after repeated
  inconclusive attempts. Uses `utils/styleAnalysis.js` for legacy normalization.
- `OnboardingWidget.jsx` displays actionable style descriptions, navigates to
  focused Profile uploads, and can reappear if an analysis needs attention again.
- Widget minimization does not discard backend progress.
- Verification: component/context tests and mobile/desktop browser journey,
  including automated accessibility checks.
