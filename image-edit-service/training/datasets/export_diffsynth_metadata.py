#!/usr/bin/env python3
"""Export DiffSynth-Studio metadata from Wardrub JSONL manifests.

DiffSynth's Qwen-Image-Edit-2511 LoRA script expects metadata with:

  image      -> target/result image to train reconstruction/noise prediction on
  edit_image -> conditioning image(s) passed to the edit model
  prompt     -> edit instruction

For Wardrub VTON:
  image      = target person wearing garment
  edit_image = [agnostic person, flat-lay garment]

For Wardrub ghost/extraction:
  image      = isolated garment / product target
  edit_image = [person wearing garment]

Paths are written relative to --dataset-root, which should be passed as
DiffSynth --dataset_base_path.
"""

from __future__ import annotations

import argparse
import json
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


def write_metadata(rows: list[dict[str, Any]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def convert_row(row: dict[str, Any]) -> dict[str, Any]:
    task = row.get("task")
    if task == "try_on":
        edit_image = [row["person"], row["garment"]]
        image = row["target"]
    elif task == "ghost_mannequin":
        edit_image = [row.get("input", row["images"][0])]
        image = row["target"]
    else:
        # Generic fallback: train target from listed conditioning images.
        edit_image = row.get("images", [])
        image = row["target"]

    return {
        "image": image,
        "edit_image": edit_image,
        "prompt": row["prompt"],
        "task": task,
        "id": row.get("id"),
        "category": row.get("category"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Wardrub JSONL manifest")
    parser.add_argument("--out", required=True, help="Output DiffSynth metadata.json")
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit; 0 means all")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(Path(args.manifest))
    if args.limit:
        rows = rows[: args.limit]
    metadata = [convert_row(row) for row in rows]
    write_metadata(metadata, Path(args.out))
    print(f"Wrote {len(metadata)} DiffSynth metadata rows to {args.out}")
    if metadata:
        print(json.dumps(metadata[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
