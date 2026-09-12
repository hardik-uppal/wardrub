"""Compare list-path CPU/IO counts with baseline using synthetic images and fake GCS.

No cloud calls, signing RPCs, network latency or real user data. Results are NOT
browser or production latency. Run from any cwd with backend deps available.
"""
import argparse
import ast
import asyncio
import hashlib
import io
import json
import platform
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from PIL import Image
from app.services.storage import StorageService
from app.services import storage as storage_module


def baseline_class(ref):
    source = subprocess.check_output(['git', 'show', f'{ref}:backend/app/services/storage.py'], cwd=ROOT, text=True)
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'StorageService')
    methods = [n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name in ('list_garments', 'list_tryon_results')]
    namespace = dict(vars(storage_module))
    exec(compile(ast.Module(body=methods, type_ignores=[]), '<baseline-listing>', 'exec'), namespace)
    return type('BaselineStorage', (StorageService,), {n.name: namespace[n.name] for n in methods})


class Blob:
    def __init__(self, name, store, counts):
        self.name, self.store, self.counts = name, store, counts
        self.metadata = {}
        self.time_created = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def download_as_bytes(self):
        self.counts['downloads'] += 1
        self.counts['download_bytes'] += len(self.store[self.name])
        return self.store[self.name]

    def upload_from_string(self, data, content_type):
        self.counts['uploads'] += 1
        self.counts['upload_bytes'] += len(data)
        self.store[self.name] = data


async def measure(cls, endpoint, count, thumbnails, image_bytes, repeats):
    samples, io_counts = [], []
    for _ in range(repeats):
        prefix = 'users/fixture/garments/top/' if endpoint == 'wardrobe' else 'users/fixture/tryon-results/'
        names = [prefix + f'{i}_front.png' for i in range(count)]
        store = {name: image_bytes for name in names}
        if thumbnails:
            for name in names:
                store[StorageService._thumbnail_path(name)] = b'preexisting-thumbnail'
        counters = dict(downloads=0, uploads=0, download_bytes=0, upload_bytes=0, signings=0, lists=0)
        def blob(name):
            return Blob(name, store, counters)
        def list_blobs(bucket, prefix):
            counters['lists'] += 1
            return [blob(n) for n in store if n.startswith(prefix)]
        def sign(name):
            counters['signings'] += 1
            return 'fake-signed:' + name
        service = cls()
        service._bucket = SimpleNamespace(blob=blob)
        service._client = SimpleNamespace(list_blobs=list_blobs)
        service._generate_signed_url = sign
        start = time.perf_counter()
        if endpoint == 'wardrobe':
            rows = await service.list_garments('fixture')
        else:
            rows = await service.list_tryon_results('fixture', limit=count)
        samples.append((time.perf_counter() - start) * 1000)
        assert len(rows) == count
        io_counts.append(counters)
    ordered = sorted(samples)
    return {'p50_ms': statistics.median(samples), 'p95_ms': ordered[max(0, __import__('math').ceil(.95 * repeats) - 1)],
            'samples_ms': samples, 'io_per_request': io_counts[0],
            'consistent_io_counts': all(c == io_counts[0] for c in io_counts)}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='a60892c')
    parser.add_argument('--repeats', type=int, default=10)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('repeats must be positive')
    # Deterministic textured PNG, not a person's photograph. Encoding isn't timed.
    image = Image.frombytes('RGB', (1536, 2048), random.Random(42).randbytes(1536 * 2048 * 3))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    payload = buffer.getvalue()
    baseline = baseline_class(args.baseline)
    report = {'kind': 'synthetic CPU microbenchmark; cloud IO simulated, no network',
              'baseline_sha': subprocess.check_output(['git', 'rev-parse', args.baseline], cwd=ROOT, text=True).strip(),
              'candidate_storage_sha256': hashlib.sha256((ROOT / 'backend/app/services/storage.py').read_bytes()).hexdigest(),
              'python': sys.version, 'platform': platform.platform(), 'image_size': [1536, 2048],
              'png_bytes': len(payload), 'repeats': args.repeats, 'cases': []}
    for endpoint in ('wardrobe', 'looks'):
        for count in (10, 50):
            for cached in (False, True):
                case = {'endpoint': endpoint, 'items': count, 'thumbnails_present': cached}
                for label, cls in [('before', baseline), ('after', StorageService)]:
                    case[label] = await measure(cls, endpoint, count, cached, payload, args.repeats)
                report['cases'].append(case)
                print(endpoint, count, cached, round(case['before']['p50_ms'], 2), round(case['after']['p50_ms'], 2), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    asyncio.run(main())
