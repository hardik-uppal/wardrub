#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--in-manifest", required=True)
    p.add_argument("--out-manifest", required=True)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--prompt", default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    src = Path(args.in_manifest)
    dst = Path(args.out_manifest)
    dst.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if args.steps is not None:
                row["steps"] = args.steps
            if args.prompt:
                row["prompt"] = args.prompt
            rows.append(row)

    with dst.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows -> {dst}")


if __name__ == "__main__":
    main()
