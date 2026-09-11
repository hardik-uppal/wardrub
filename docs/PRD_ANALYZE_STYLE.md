# Analyze Style — Product Spec

Status: MVP implementation authorized on 2026-09-11; see implementation plan and progress ledger
Owner: Hardik
Created: 2026-09-11
Branch: `codex/analyze-style-spec`

## Implementation scope

Hardik ended discovery with: "lets go and finish the implementation, and build
the tests for it". The interviewed color-first flow, fit follow-ups, backend
progress, and onboarding guidance form the MVP. Engineering choices resolving
the remaining questions are recorded in `docs/IMPLEMENTATION_ANALYZE_STYLE.md`.
The interview record below preserves which decisions were explicit versus
proposed at the time; unresolved future enhancements do not block this MVP.

Implementation details: independent `color` and `fit` states are persisted in
`style_analysis`; usable results remain in existing `skin_tone`, `body_type`,
and `body_measurements` fields. Loading is transient UI state. Failed attempts
are distinct from photo requests and never discard usable results. Initial
entry remains explicit Profile uploads. See
`docs/progress/analyze-style-PROGRESS.md` for verification.

## Confirmed intent

Hardik wants to build the Analyze Style service for Wardrub and define its
product spec through an interview before implementation.

Original request:

> i want to build the anlyze style service for my wardrub app, can you aopen a branch and define the product spec for it with an interview with me?

## Existing product context

These are observations from the repository, not decisions about the new scope.
Runtime behavior has not been verified as part of this discovery.

- Profile has an Analyze Style photo-upload flow and displays seasonal colors,
  undertone, body type, color recommendations, and fit guidance.
- `POST /api/profile/analyze` assesses uploaded photo quality, selects the
  highest-quality image, runs color and body analysis, and saves a user profile.
- The endpoint preserves existing style preferences and location. It returns
  confidence-related feedback and recommendations for additional photos.
- `POST /api/create-avatar-full` exposes an option to combine avatar creation
  with profile analysis.
- Existing backlog item ENH-001 proposes AI style/color analysis in Profile and
  possibly onboarding. Its MVP is a hypothesis, not an agreed requirement.
- The onboarding widget already links an Analyze your style milestone to
  Profile. Its context currently marks that milestone complete if either skin
  tone or body type exists, without distinguishing analysis stages.
- Wardrub's product process emphasizes useful recommendations, owned wardrobe
  first, and learning from user feedback.

References: `frontend/src/pages/Profile.jsx`, `backend/app/routers/profile.py`,
`backend/app/routers/avatar.py`, `frontend/src/context/OnboardingContext.jsx`,
`docs/PRODUCT_DEVELOPMENT_PROCESS.md`.
ENH-001 is in the pre-existing local, untracked `docs/PRODUCT_BACKLOG.md`.

## Interview plan

Use short rounds and record answers before turning them into requirements.

1. Target user, triggering problem, and the main benefit of analysis.
2. Inputs and entry points: photos, preferences, wardrobe, Profile, onboarding.
3. Results: what users see, what they can do next, and how personalization uses it.
4. User control: corrections, uncertain results, retries, photo handling, deletion.
5. MVP boundaries, success criteria, latency/cost expectations, and rollout.

## Product direction — confirmed through round 3

### User benefit

Help users discover flattering colors and fits and put together better outfits.
Use the analysis to tailor suggestions to their existing wardrobe. Potentially
suggest swapping pieces that do not serve the user well; the meaning of a swap
and whether this belongs in the first release remain open.

### Progressive analysis

- Analysis is an iterative, multi-step process, not a single upload and final report.
- Begin with skin tone/color analysis.
- Add body type/fit analysis when the user provides full-length photos.
- Ask for additional photos of a specific type when the available images do not
  provide enough evidence. This applies independently to color and body analysis.
- Loose-fitting clothing is an explicit ambiguity case for body analysis and may
  require a targeted clarification or photo request.

The user's desired endpoint is sufficient certainty to make useful suggestions.
How to judge sufficient evidence, communicate uncertainty, and stop requesting
photos when the evidence remains inconclusive is still to be defined. No
numerical confidence threshold or guarantee of certainty has been agreed.

### First result and onboarding guidance

- The first result should suggest flattering colors. Body/fit analysis is a later
  stage and is not a prerequisite for this initial value.
- Use the existing onboarding widget to guide users through the analysis stages.
- The precise palette presentation, explanations, and timing of wardrobe-level
  recommendations remain open; the confirmed starting point is color suggestions.

Once color recommendations are available, keep them available and have the
onboarding widget explain that adding a full-length photo enables better fit
analysis. Users can receive color value while the fit stage remains pending.
Backend-maintained progress should support this guidance across stages.

Suggested widget copy: "Your color recommendations are ready. Add a full-length
photo for better fit analysis." Exact copy, dismissal/reminder behavior, and the
definition of overall onboarding completion remain open.

### Backend progress schema — proposed shape

Hardik proposed a backend schema to maintain the staged experience. The following
shape translates that direction into a reviewable proposal; field names and API
contracts are not finalized.

Maintain independent `color` and `fit` analysis records under the user's profile:

| Field per analysis | Purpose |
|---|---|
| `status` | `not_started`, `needs_input`, `analyzing`, `ready`, or `failed`; describes the current analysis attempt. |
| `result` | Latest usable result, if any; preserve it while another attempt is pending or fails. |
| `evidence_assessment` | What the photos support, unresolved issues, and why more evidence is needed; criteria remain to be defined. |
| `requested_input` | Structured photo type, reason, and user-facing instructions for the next useful upload; absent when no input is needed. |
| `updated_at` / `result_updated_at` | Track progress updates separately from the age of the usable result. |

For the confirmed initial journey, color has a usable result while fit requests
a full-length photo. The widget reads backend progress to display the next
action. Recommendation consumers use available results independently, so missing
fit analysis does not block color recommendations.

Proposed behavior to validate during implementation planning:

- Resume the current stage after leaving and returning to the app.
- Preserve a usable color result when a fit upload is insufficient or fails.
- Explain why a replacement photo is needed, such as loose clothing obscuring
  body proportions, without claiming that repeated uploads guarantee certainty.
- Treat service failures separately from inadequate photo evidence; do not ask
  for a new photo just because a request failed.

This is an extension proposal for the existing profile model, not a decision to
deploy a separate service. Photo storage/retention and migration of existing
profiles remain open.

### Candidate user stories derived from this direction

- As a user, I want to learn which colors and fits flatter me so I can assemble
  better outfits using my wardrobe.
- As a user starting with photos suitable for color analysis, I want to develop
  my profile over time as I add full-length photos.
- As a user whose photos are ambiguous, I want a specific request that explains
  what additional image would help the analysis.

### Implementation implications to investigate later

The existing endpoint selects one highest-quality image for both analyses.
Progressive analysis will require considering which evidence is suitable for
each analysis and how later uploads refine saved results. API contracts,
persistence behavior, and the service boundary remain undecided.

The widget's current single completion flag cannot distinguish colors available
from body/fit analysis still pending. The product spec must define stage progress
and completion before choosing how to change that flag or the milestone layout.

## Product definition — remaining interview decisions

| Area | Decision needed |
|---|---|
| Problem and target user | Who needs this, in what situation, and why? |
| Primary outcome | Flattering color suggestions first; refine palette presentation and next actions. |
| Goals | Which user and business outcomes matter for the first release? |
| User stories | What concrete journeys must the service support? |
| Inputs | Which inputs are required, optional, or reusable? |
| Entry and completion | Widget retains color value and invites a full-length photo; define initial entry, reminders, and overall completion. |
| Results and next action | What appears in the report and connects to the wardrobe? |
| MVP and non-goals | What ships first and what is deferred? |
| Empty/error/partial states | What happens when inputs or analysis are insufficient? |
| User control and photo lifecycle | What can users correct, retry, retain, or delete? |
| Data/API implications | Backend stage tracking proposed above; finalize contracts and existing-profile migration. |
| Service boundaries | Is this an existing backend capability or a separate service? |
| Success and acceptance criteria | What evidence demonstrates a useful, reliable release? |
| Risks and constraints | What quality, latency, cost, and operational limits apply? |

## Interview record

### Round 1 — Primary user benefit

Question: Imagine a user taps Analyze Style and gets a great result. What should
they now understand or be able to do that they couldn't before?

Answer (user's wording):

> discover flatter colors and fits, and put together better outfits, it would also help us tailor right suggestions for them in their wardobe and maybe swap peices which does not do them justice that are currently there. it would be an iterative and multi step process. first is analyzinf skin tones etc and then getting thier body type when they do add full length pictures as well. we might need calrity if they do add more loose fitted clothes. we need to ask for more images of a certains type till we are certain. same for skin analyses.

### Round 2 — Value from the first stage

Question: For a user who has only provided photos suitable for color analysis,
what should their first result contain, including any wardrobe suggestions?

Answer (user's wording):

> it should start with suggesting right color and our onboarding widget should guide them accross

### Round 3 — Optional steps and continuation

Question: How should the onboarding widget behave if a user has their color
suggestions but does not want to upload a full-length photo yet?

Answer (user's wording):

> it would start with recommendations on color and let user know for better fit analysis add fill length photo, we could have aschema iin the backend maintaining this

### Round 4 — Initial photo source

Question: Should color analysis begin automatically from the original photo the
user uploads to create their avatar?

Answer: Pending. This question refers to the user's original photo, not a
generated avatar image.

## Decisions

- 2026-09-11: Focus analysis on flattering colors, fits, and better outfits, with
  personalization of the user's existing wardrobe.
- 2026-09-11: Build the profile progressively: color analysis first, followed by
  body/fit analysis when full-length photos are supplied.
- 2026-09-11: Request targeted additional images when evidence is insufficient,
  including ambiguity caused by loose clothing or unsuitable color-analysis photos.
- 2026-09-11: Deliver flattering color suggestions as the first result and use
  the existing onboarding widget to guide users through subsequent stages.
- 2026-09-11: Keep color recommendations available while inviting a full-length
  photo for better fit analysis. Use backend progress tracking to maintain the
  staged experience; the detailed schema above is a proposal.
- Piece swaps are a possible extension; scope and behavior are not yet decided.
- Existing implementation behavior is background, not approved future scope.
