"""Reproducible synthetic correctness comparison; not a taste-quality benchmark."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.models.garment import GarmentMetadata
from app.services.closet_ranker import ClosetRanker, eligible, valid_outfit
from app.services.outfit_scorer import OutfitScorerService


def evaluate(path):
    rows = []
    ranker, legacy = ClosetRanker(), OutfitScorerService()
    for line in Path(path).read_text().splitlines():
        case = json.loads(line)
        clothes = [GarmentMetadata(user_id='benchmark', **g) for g in case['garments']]
        known = {g.garment_id: g for g in clothes}
        before = legacy.generate_top_outfits(clothes, None, case.get('weather'), limit=4)
        started = time.perf_counter()
        after = ranker.rank(clothes, 'benchmark', weather=case.get('weather'))
        elapsed = (time.perf_counter() - started) * 1000
        def check(outfits):
            violations = sum(not valid_outfit(items) or any(not eligible(g, 'benchmark') for g in items) for items in outfits)
            expected = bool(outfits) == case['expect_outfit']
            preferred = not case.get('top_must_include') or (bool(outfits) and case['top_must_include'] in {g.garment_id for g in outfits[0]})
            return {'violations': violations, 'passes': violations == 0 and expected and preferred}
        rows.append({'id': case['id'], 'legacy_scorer': check([[known[gid] for gid in o.garment_ids] for o in before]),
                     'closet_rules_v1': check(after), 'ranking_ms': round(elapsed, 2)})
    return {'manifest': str(path), 'cases': len(rows), 'results': rows,
            'legacy_passed': sum(r['legacy_scorer']['passes'] for r in rows),
            'candidate_passed': sum(r['closet_rules_v1']['passes'] for r in rows),
            'max_ranking_ms': max(r['ranking_ms'] for r in rows)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = evaluate(args.manifest)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'results'}, indent=2))
    raise SystemExit(result['candidate_passed'] != result['cases'])
