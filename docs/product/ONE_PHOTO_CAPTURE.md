# One-photo capture and quieter controls

Founder direction, 2026-09-13: adding clothes should need one picture, without front/back setup or manual labels. Photos of clothes being worn should preserve visible fit information. Reduce persistent text, buttons and filters after the first minimalist release.

## Implemented experience

Add clothes → choose a photo or take one → preview → Add clothes → automatically labeled pieces → Done. Camera and gallery use the same detection/extraction endpoint. One photo may contain multiple garments. Existing optional batches remain capped at five photos, ten MB each. No category, second view or cleanup decision is required. Camera failure falls back to the device's photo input; a late camera permission response is closed after leaving.

Wardrobe keeps search visible and puts category/readiness/sort behind one Filters disclosure, with an active indicator. Today drops repeated setup guidance and empty location labels. Detailed fit is secondary within garment detail.

## What the model records

The existing configured text model detects each garment from the original normalized photo before image cleanup: category, short label, description, style tags and fit_observation. The optional observation has source (worn/hanging/flat/unknown), apparent fit, visible length, drape, evidence, confidence, visibility and original_photo basis. Confidence is a model assertion, not measured accuracy. Fit remains unknown for non-worn, partly obscured, low-confidence or unsupported cases; malformed optional fit does not destroy a valid garment label.

Observed fit describes the person pictured. It is not the account owner's body profile, exact size, comfort, preferred cut or a promise of physical fit. It does not replace the legacy garment fit_type or train preferences. Original source and generated garment image remain separately stored; fit is never inferred from the generated mannequin.

Labels and fit are persisted and joined to wardrobe reads, preserving fresh image URLs. Unavailable optional metadata keeps images usable. New capture requires confirmed metadata writes with production fallback disabled. Successful pieces are returned even if another extraction fails; the UI asks for only missing pieces rather than retrying the whole partially saved photo. Lost HTTP responses remain uncertain and require checking the wardrobe before an explicit retry; resumable/idempotent import jobs remain future work.

## Validation and limits

Local isolated backend tests cover source preservation, fit uncertainty, invalid/bounded detections, user isolation, reload and partial success. Browser tests cover both photo inputs and collapsed filters alongside existing full journeys and nine-view light/dark accessibility checks. Fixtures are synthetic and do not exercise physical cameras or real inference.

`training/benchmarks/clothing-capture/v1` has 2 starter / 24 small parsed-response contract cases, with a before/after runner and prompt hash under `runs/2026-09-13-one-photo`. Candidate24/24 vs previous persistence20/24 measures preservation/abstention, not vision accuracy. Recommender correctness remains24/24. A consented real-photo evaluation is still required to validate extraction fidelity and apparent-fit accuracy; the benchmark README specifies the corpus and rubric. No paid model runs, deployment or old-photo re-analysis is performed by this change.
