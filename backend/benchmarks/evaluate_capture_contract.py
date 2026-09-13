"""Fixed parsed-response/persistence contract evaluation, NOT model accuracy."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.clothing_detection import normalize_detections, DETECTION_PROMPT


def evaluate(path):
    results = []
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        # The previous upload path saved category/description only, losing fit evidence.
        legacy_fit = 'unknown'
        output = normalize_detections([row['detected']])[0]
        candidate_fit = output['fit_observation']['fit']
        results.append({'id':row['id'], 'legacy_pass':legacy_fit == row['expected_fit'],
                        'candidate_pass':candidate_fit == row['expected_fit'],
                        'expected':row['expected_fit'], 'actual':candidate_fit})
    return {'kind':'parsed-response contract; not visual model accuracy', 'manifest':str(path),
            'prompt_sha256':hashlib.sha256(DETECTION_PROMPT.encode()).hexdigest(),
            'cases':len(results), 'legacy_passed':sum(r['legacy_pass'] for r in results),
            'candidate_passed':sum(r['candidate_pass'] for r in results), 'results':results}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('manifest'); parser.add_argument('--output',required=True)
    args=parser.parse_args(); result=evaluate(args.manifest)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
    raise SystemExit(result['candidate_passed'] != result['cases'])
