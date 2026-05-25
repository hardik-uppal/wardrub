#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--viton-root", default="data/viton_hd_proto")
    p.add_argument("--viton-manifest", default="data/viton_hd_proto/manifests/tryon_train.jsonl")
    p.add_argument("--out-assets", default="training/benchmarks/assets/chunks/fullbody_viton_small_v1/persons")
    p.add_argument("--out-manifest", default="training/benchmarks/avatar_fullbody_viton_small_v1.jsonl")
    p.add_argument("--count", type=int, default=48)
    p.add_argument("--steps", type=int, default=24)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    repo = Path(args.repo_root).resolve()
    viton_root = (repo / args.viton_root).resolve()
    manifest_path = (repo / args.viton_manifest).resolve()

    rows = read_jsonl(manifest_path)
    if not rows:
        raise SystemExit(f"No rows in {manifest_path}")

    rng = random.Random(args.seed)
    sample = rows if args.count >= len(rows) else rng.sample(rows, args.count)

    out_assets = (repo / args.out_assets).resolve()
    out_assets.mkdir(parents=True, exist_ok=True)

    out_rows = []
    for i, r in enumerate(sample):
        sid = str(r["id"])
        src = viton_root / r["person"]
        if not src.exists():
            continue
        dst = out_assets / f"{sid}_person.png"
        shutil.copy2(src, dst)
        rel = dst.relative_to(repo).as_posix()
        out_rows.append(
            {
                "id": f"fullbody_{i:04d}",
                "endpoint": "edit",
                "image": rel,
                "prompt": "Create a full-body neutral standing avatar (front-facing, arms relaxed) on a plain background. Preserve exact facial identity, skin tone, body proportions, and key appearance details.",
                "steps": args.steps,
                "tags": {
                    "source_type": "fullbody_person",
                    "origin": "viton_hd_proto",
                    "split": "eval",
                },
            }
        )

    out_manifest = (repo / args.out_manifest).resolve()
    write_jsonl(out_manifest, out_rows)

    print(f"Wrote {len(out_rows)} rows -> {out_manifest}")
    print(f"Assets dir: {out_assets}")


if __name__ == "__main__":
    main()
