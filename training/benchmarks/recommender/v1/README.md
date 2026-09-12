# Recommender correctness benchmark v1

24 hand-authored synthetic closet/context scenarios; `starter.jsonl` is the two-case
smoke subset. No real people, private identifiers, images, or external datasets.
These fixtures test closet decisions, not virtual-try-on fidelity or personal taste.

Run from the repository root with backend dependencies installed:

```sh
PYTHONPATH=backend python backend/benchmarks/evaluate_recommender.py training/benchmarks/recommender/v1/starter.jsonl --output runs/<run>/starter.json
PYTHONPATH=backend python backend/benchmarks/evaluate_recommender.py training/benchmarks/recommender/v1/small.jsonl --output runs/<run>/comparison.json
```

Use a credential-free test environment with dotenv loading disabled. No provider
calls occur in the evaluator. Input data and tie-breaks are fixed; timestamps and
measured runtime do not affect scoring. `OutfitScorerService.generate_top_outfits`
is the unchanged legacy scorer from baseline commit `d754dda`; `ClosetRanker` is the
candidate. The old ten-item API gate and Gemini editorial stage are deliberately
excluded, so this comparison isolates deterministic candidate generation/ranking.

## Rubric

A case passes when all returned outfits have a valid core (top + bottom or dress,
plus optional unique outerwear/shoes), no garment is known unavailable/unowned,
existence/absence matches `expect_outfit`, and the leading outfit contains
`top_must_include` where specified. Missing readiness is allowed, not treated as
confirmed clean; disclosure is verified separately by service/UI tests.

The benchmark records hard violations, per-case pass/fail, and candidate ranking
latency. No probabilistic match accuracy or causal business lift is claimed.

## Scale-up

Add large-closet and held-out user/context scenarios with consent and garment
attributes validated by their owners. Keep real assets/private IDs outside Git;
version a sanitized manifest and rubric. Evaluate temporal splits and contextual
pairwise preference agreement before training. Report uncertainty and capture
burden in a pilot; synthetic correctness alone does not establish outfit appeal.
