# Wardrub Product Development Process

**Status:** Draft for review  
**Owner:** Hardik + Bud  
**Created:** 2026-05-24

---

## 1. Why This Exists

Wardrub should not be built as a pile of cool experiments. We need a lightweight product-management process so each feature answers:

1. What user problem are we solving?
2. Why now?
3. What is the smallest useful version?
4. How will we know it worked?
5. What do we explicitly not build yet?

This doc defines how we take ideas from rough thoughts to shipped product.

---

## 2. Product Operating Model

We will use a simple product loop:

```text
Idea → PRD → Review → Milestone Plan → Build → QA → Learn → Iterate
```

This is deliberately lightweight. No corporate theater. Just enough structure to stop us from chasing shiny objects like raccoons with GPUs.

---

## 3. Required Docs for Meaningful Features

Every significant feature should have the following:

### 1. PRD / Product Spec

Answers:

- user problem,
- target user,
- goals,
- non-goals,
- user stories,
- MVP scope,
- data model/API implications,
- success metrics,
- risks,
- open decisions.

Example:

- `docs/PRD_MAGAZINE_FEED.md`

### 2. Implementation Plan

Answers:

- technical approach,
- frontend changes,
- backend changes,
- data migrations,
- services/models needed,
- phased tasks,
- test plan.

Suggested path:

```text
docs/IMPLEMENTATION_<FEATURE>.md
```

### 3. Progress Tracker

Answers:

- what is done,
- what is in progress,
- what is blocked,
- what changed from the original plan.

Suggested path:

```text
docs/progress/<feature>-PROGRESS.md
```

### 4. Decision Log

For product/architecture decisions that may matter later.

Suggested path:

```text
docs/DECISION_LOG.md
```

---

## 4. Feature Lifecycle

### Stage 0: Raw Idea

A rough note, chat message, voice note, or ThoughtOS capture.

Example:

> Build a magazine-like feed using clothes the user already owns. Vanika suggested chatbot interface.

Output:

- captured note,
- maybe linked task,
- no code yet unless it is a tiny experiment.

### Stage 1: Product Spec / PRD

Turn the raw idea into a concrete product doc.

Output:

- PRD created,
- open questions listed,
- MVP/non-goals defined.

Rule:

> If we cannot explain the MVP in one paragraph, we are not ready to build.

### Stage 2: Review

Hardik + Bud review the PRD.

Review questions:

1. Is this actually useful?
2. Is the MVP small enough?
3. Are we solving the right first user problem?
4. What are we intentionally delaying?
5. What metric tells us this worked?

Output:

- PRD status moves from `Draft` to `Approved for implementation`, or stays draft with edits.

### Stage 3: Implementation Plan

Create a technical plan after PRD review.

Output:

- implementation doc,
- milestone checklist,
- data/API contracts,
- test plan.

Rule:

> No large feature coding without an implementation plan.

Exceptions:

- throwaway experiments,
- quick UI spikes,
- bug fixes,
- investigative scripts.

### Stage 4: Build in Milestones

Build small vertical slices.

Preferred milestone shape:

1. Data model / backend contract.
2. Minimal working backend logic.
3. Minimal UI.
4. Persistence.
5. Feedback loop.
6. Polish.

Each milestone should be demoable.

### Stage 5: QA + Product Review

Before calling a feature done:

- run tests/build/lint where applicable,
- inspect UX manually,
- check mobile layout,
- verify data persistence,
- verify error/empty states,
- compare output against PRD.

### Stage 6: Learn + Iterate

After shipping:

- collect feedback,
- inspect metrics,
- update PRD if assumptions changed,
- add next iteration plan.

---

## 5. Review Checklist for PRDs

Before implementation, every PRD should answer:

- [ ] Who is this for?
- [ ] What user pain does it solve?
- [ ] What is the smallest valuable version?
- [ ] What is out of scope?
- [ ] What user action starts the flow?
- [ ] What user action completes the flow?
- [ ] What should happen in empty/error states?
- [ ] What data do we need?
- [ ] What can be manually faked or stubbed in MVP?
- [ ] What metric proves usefulness?
- [ ] What are the biggest risks?
- [ ] What decisions need Hardik review?

---

## 6. Product Principles for Wardrub

### 1. Utility Before Magic

A useful outfit recommendation beats a flashy but wrong generated try-on.

### 2. Taste Beats Volume

Do not drown users in options. Curate fewer, better looks.

### 3. Owned Wardrobe First

Wardrub’s differentiator is using what the user already owns.

### 4. Feedback Is Product Gold

Every save, dislike, and “I wore this” should improve recommendations.

### 5. VTON Is a Layer, Not the Whole Product

Virtual try-on can make the product magical, but the core loop should still work without it.

### 6. Build Daily Habits

The long-term winning loop is daily/weekly style guidance, not one-off image generation.

---

## 7. Current Product Bets

### Bet 1: Magazine Feed

Users will find value in curated outfit suggestions from their own closet, even without photorealistic try-on.

Spec:

- `docs/PRD_MAGAZINE_FEED.md`

### Bet 2: VTON / Avatar Generation

High-quality try-on will become a premium layer once users trust the outfit recommendations.

Existing docs:

- `README.md`
- `image-edit-service/README.md`

### Bet 3: Chrome Extension / Web Capture

Wardrub can become more useful if users can save clothing from shopping sites easily.

Existing docs:

- `docs/CHROME_EXTENSION_PLAN.md`

---

## 8. Suggested Doc Structure

```text
docs/
  PRODUCT_DEVELOPMENT_PROCESS.md
  DECISION_LOG.md
  PRD_MAGAZINE_FEED.md
  IMPLEMENTATION_MAGAZINE_FEED.md
  progress/
    magazine-feed-PROGRESS.md
```

We do not need every file immediately. Create docs as features move forward.

---

## 9. Immediate Next Steps

1. Review `docs/PRD_MAGAZINE_FEED.md`.
2. Answer open decisions in that PRD.
3. Update PRD to `Approved for implementation` once aligned.
4. Create `docs/IMPLEMENTATION_MAGAZINE_FEED.md`.
5. Break implementation into 3–5 milestones.
6. Build the first vertical slice:
   - use existing wardrobe items,
   - generate simple outfit cards,
   - render a feed page.

---

## 10. Hardik + Bud Review Ritual

For each major feature:

1. Bud drafts the PRD.
2. Hardik reviews product direction and open questions.
3. Bud updates the spec.
4. Bud drafts implementation plan.
5. Build starts only after scope is clear.

Keep it sharp. Keep it practical. Ship useful things.
