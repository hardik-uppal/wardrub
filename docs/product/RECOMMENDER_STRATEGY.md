# Wardrub recommender strategy

Companion to [the mission](WARDRUB_MISSION.md). Proposed architecture and rollout,
not a claim that these capabilities are already implemented.

## 1. The decision we are trying to make

“What would this person be happy to wear today, from clothes they own, can access,
and have ready—with as little work as possible?”

This is constrained, contextual outfit ranking plus closet management. It is not
primarily text/image generation, a shopping recommender, or a universal fashion
score. A beautiful suggestion containing an unavailable garment is a bad result.

## 2. Current implementation: useful foundation, not a learned brain

Source inspected: `outfit_scorer.py`, `magazine_feed_service.py`, and garment/feed
models under `backend/app`.

- `OutfitScorerService` builds combinations and scores weather (30%), color harmony
  (35%), style cohesion (20%) and versatility (15%). These are engineering defaults,
  not learned or validated personalized weights.
- `MagazineFeedService` passes candidates and closet details to Gemini, which also
  curates final looks. Model-returned scores populate cards; do not interpret them
  as calibrated probabilities that a user will like or wear an outfit.
- Weather is read at generation from the saved profile location; missing weather
  falls back to a misleading 20 C / clear value. Cached reads bypass weather.
- Feeds cache by user/date, with a 10-garment generation prerequisite. The updated
  direction is input-driven reuse rather than automatic daily editorial generation.
- Feedback schema has `look_id`, action and time. Look IDs are freshly randomized
  on generation. `disliked_look_ids` is computed in generation but not used later.
  Recording feedback therefore does not currently establish effective preference
  learning or durable avoidance across regenerated editions.
- The inspected garment schema has no explicit laundry/readiness or physical
  storage-location lifecycle. Do not imply the app can already track either.

## 3. Proposed architecture

```text
Capture / corrections     Wear / laundry / move actions     Optional preferences
          \                         |                             /
           +------------------------+----------------------------+
                                    v
                    Private wardrobe state + event history
                  (attributes, confidence, availability, location)
                                    |
                     +--------------+---------------+
                     |                              |
                 Context                       Learned preferences
        Weather + optional occasion          Regularized, explainable
        + user's explicit needs              per-user adjustments
                     |                              |
                     +--------------+---------------+
                                    v
                  Eligibility checks and candidate construction
                                    v
                      Outfit compatibility / utility ranking
                                    v
                  Diversity + repetition + reasonable rotation
                                    v
                      1 best option + a few alternatives
                    Where to find it / why it suits today
                                    |
                    Choose / swap / wore / unavailable / skip
                                    +----> state and learning updates

Optional editorial and try-on presentation sit downstream, not in the critical
ranking loop. Gemini must not silently reintroduce ineligible items.
```

### Separate facts, hypotheses and taste

- **Facts:** ownership, confirmed laundry state, explicitly retired/lent items,
  confirmed storage location, recorded wear, weather observation and its timestamp.
- **Hypotheses:** estimated warmth, material, style tags, possible physical location;
  retain provenance/confidence and allow correction.
- **Taste:** preferred silhouettes, palettes, contrast, formality, combinations and
  tolerance for repetition. Learn rather than declaring universal correctness.

Eligibility enforces ownership and known unavailability. Weather comfort and most
style conventions are soft constraints unless the user makes them explicit needs.
Unknown readiness is not the same as dirty or clean: show uncertainty and make
confirmation easy. Missing weather is not evidence of mild weather.

## 4. Cold start: value first, questions only when useful

### No wardrobe yet

Guide capture of a handful of frequently worn items that can form one useful
outfit, not an arbitrary collection count. A top and bottom can be enough for a
limited suggestion; do not imply completeness when shoes/layers are unknown.
Batch capture, suggest categories, let users approve/correct quickly, and show
“you can make these combinations” as an immediate reward. Add the rest gradually.
Separate fast indexing from optional expensive mannequin generation.

### Clothes present, little preference history

Use a conservative content-based prior: compatible categories/layers, warmth,
color relationships, silhouette/formality, and known occasion. Optional confirmed
skin-tone/season results can influence a weak color prior; they must not dominate
expressed taste or block onboarding. Saved location is optional; label generic
recommendations when absent. Defaults and confidence should be visible/editable.

Offer at most a small optional “which would you wear?” choice between outfits
constructed from the user's own items when it can resolve a real uncertainty.
Accept skip; do not turn preference discovery into a mandatory quiz. A newly added
item also has cold start: attributes and known compatible pieces provide a prior
without requiring interaction history for that item.

## 5. Learning preferences: the brain grows from decision evidence

### Instrument before training

Store a stable outfit key from the canonical set of garment IDs (and relevant
layer/role assignments), scoped to the user. Keep presentation-card IDs separate.
Record private decision events with an idempotent event ID, request/slate ID,
shown candidates and order, actually visible exposure, context/availability
snapshot, relevant garment versions, policy version, action and timestamp.

Do not equate an API response with an impression. Without knowing what was seen
and available, “not selected” is ambiguous. Separate training attributes from PII;
keep raw event history private, never in public GitHub issues or unrestricted logs.

### Give actions different meanings

| Signal | Interpretation |
|---|---|
| Confirmed “wore this” | Strong usefulness evidence; update wear history |
| Chose this instead of an exposed alternative | Contextual relative preference |
| Saved / liked | Interest, weaker than actual use |
| Swapped one item | Learn at outfit/compatibility level, not dislike of all items |
| “Not my style” | Aesthetic negative, within context |
| “Too warm / too formal” | Contextual mismatch; do not globally ban the item |
| “In wash / cannot find / no longer own” | Availability correction, not taste |
| No click / no wear confirmation | Unknown; not automatically a negative |

Selection is not confirmed wear. Wearing an outfit is not proof every component
was liked. Keep contextual negatives and long-lived preferences separate. Offer
optional one-tap reasons and accept an unlabelled skip; feedback itself must be
low friction.

### Start small and regularized

1. Ship reliable rule-based/content-based ranking and meaningful action semantics.
2. Add conservative per-user adjustments from explicit feedback. Shrink sparse
   preferences toward a shared hand-designed baseline; keep user overrides ahead
   of inferred preferences. Cap update strength and allow recent evidence to
   outweigh old habits without erasing stable preferences after one event.
3. Once there is sufficient exposure/choice data, evaluate a small regularized
   contextual or pairwise ranker (for example logistic ranking). Features include
   compatibility, user-item affinity, occasion, warmth fit, formality, rotation and
   recent repeats. Avoid training a separate unconstrained model per new user.
4. Add a shared learned prior/collaborative features only when enough suitable,
   privacy-safe data exists. Each closet contains different items, so item-ID
   collaborative filtering alone is a poor cold-start foundation; shared attributes
   and outfit relationships generalize better.
5. Later consider a contextual bandit for limited exploration among eligible,
   reasonable alternatives. Keep the primary morning recommendation reliable;
   provide an optional “try something different” alternative. Record the actual
   sampling propensity if randomization is used. No bandit rollout without a
   baseline, safety rules, exposure logging and online evaluation.

We do not need a GPU or a large model to start. Do not pretend a fixed number of
clicks guarantees readiness: promote models based on held-out and user evidence.

### Rank, then choose a useful slate

After eligibility, a conceptual utility combines context fit, outfit compatibility,
learned preference and reasonable wardrobe rotation, minus repetition and friction.
Weights are hypotheses to validate, not probabilities. Personalize repetition:
some people value a reliable uniform. Underused pieces deserve an opportunity,
not forced inclusion over comfort, fit, readiness or preference.

Return one actionable option and a few meaningfully different alternatives—not
three near-identical outfits or an overwhelming magazine. Explanations should be
traceable: “available, suitable for today's temperature, and similar to combinations
you wore,” only when each claim is supported.

## 6. Closet state: the recommender's source of truth

Proposed orthogonal fields: ownership/lifecycle, readiness (unknown/ready/laundry/
needs-care), physical location (optional user label and confirmation time), and wear
history. “Clean” does not necessarily mean “in the drawer.”

Use an append-only event ledger plus a current-state projection: garment added,
corrected, worn, sent to laundry, returned, moved, lent, repaired, retired. Events
need idempotency, server ordering/version checks, user scoping and undo/correction
semantics so retries or offline sync do not corrupt availability.

**Minimum useful loop:** confirm outfit worn → optionally select which pieces go
into laundry → mark a batch ready when returned. Do not mark every worn item dirty
or automatically mark laundry clean after a timer. Use garment icons and batch
actions; optional defaults must be confirmed and reversible. Do not ask for shelf
location every time an item is worn.

Care guidance should follow confirmed care labels/materials, not guess washing
instructions from an image. Notifications are opt-in, sparse and actionable.
No sensors, cameras or autonomous physical tracking are assumed.

## 7. Freshness and cost boundaries

- Recompute eligibility immediately after availability/ownership changes.
- Refresh saved-location weather on a bounded TTL; re-rank cheaply when meaningful
  conditions change. Store source, location, observation/fetch time and staleness.
- Version wardrobe attributes, relevant profile/preferences and ranking policy.
  Invalidate affected candidate/ranking caches on those changes, not just additions.
- Cache reusable compatibility work and optional editorial independently. A laundry
  change or midnight does not inherently justify a new Gemini call.
- Keep context-dependent copy out of long-lived editorial; regenerate a small
  grounded explanation or use rule templates when weather/context changes.
- Preserve an explicit user-requested creative refresh as a separate operation.

## 8. Evaluation: prove we remove effort

Primary outcome candidates: time to choose a usable outfit, confirmed-wear rate
among exposed recommendations, and availability/location mismatch rate. Also
track first useful outfit completion, correction burden, repeat/rotation balance,
wardrobe coverage, latency and cost per useful recommendation. Watch response
bias: unconfirmed wear is missing evidence, not a failed recommendation.

Build a versioned, private evaluation set alongside the pipeline: begin with a
small synthetic smoke set, then 20–50 consented user/context scenarios. Include
new users, small/large wardrobes, missing location/profile, changed weather,
laundry, unavailable favorites, repeated outfits, ambiguous preference feedback,
and newly added garments. Keep private images and IDs out of git; commit only
sanitized fixtures/manifests and scoring code. Use appropriate ranking manifests,
not virtual-try-on image-pair benchmarks, for this task.

Compare baseline and candidate on the same scenarios. Check hard-constraint
violations (target zero for known unavailability/ownership), pairwise preference
agreement, top-k usefulness and diversity. Temporal splits must prevent training
on future actions. Evaluate cold users/items separately. Small-data results need
uncertainty reporting and qualitative review; logged rankings have exposure bias,
so do not claim causal gains from offline replay without justified assumptions.

Online, start with a small consented pilot and optional shadow ranking without
extra generation calls. Promote a challenger only if it reduces effort/improves
usefulness without worsening availability accuracy, privacy, costs or friction.
Clicks and time spent scrolling are not the north star. Longer garment life needs
longitudinal evidence; cost-per-wear and rediscovery are proxies, not proof.

## 9. Recommended implementation order

1. **Correct recommendations now:** #11 weather truthfulness/input-driven caching;
   persist grounded ranker results separately from editorial. Add baseline cases.
2. **Make the daily action real:** stable outfit identity, shown/selected/swapped/
   wore events, and explicit skip reasons; verify behavior across regeneration.
3. **Add minimal availability:** ready/laundry/unknown, reversible batch actions,
   exclusion of unavailable pieces. Optional physical-location labels.
4. **Reduce cold-start friction:** useful small-wardrobe path, enjoyable progressive
   capture, and reuse existing approved inputs (#21/#18). No biometric dependency.
5. **Learn modestly:** conservative preference updates, then compare a small
   contextual ranker to rules once the data supports it.
6. **Expand carefully:** richer care/location history, optional exploration and
   learned shared priors after demonstrated value.

For each step: focused PR, explicit state/event contracts, before/after evaluation,
and updated module memory. These proposals should be split into implementation
issues before coding; this document does not launch infrastructure, training,
biometric processing or continuous user tracking.
