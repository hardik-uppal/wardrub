#!/usr/bin/env python3
"""Run a tiny Wardrub image-service eval against a prepared JSONL manifest.

Usage examples:

  # Terminal 1
  #   cd image-edit-service && source venv/bin/activate && python main.py

  # Terminal 2
  python training/eval/run_service_eval.py \
    --manifest data/viton_hd_proto/manifests/tryon_train.jsonl \
    --dataset-root data/viton_hd_proto \
    --endpoint try-on \
    --limit 5 \
    --out runs/eval_tryon_proto

The script saves returned PNGs and metrics.json for quick local 4090 debugging.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import httpx


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_base64_png(image_b64: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(image_b64))


def post_tryon(client: httpx.Client, base_url: str, root: Path, row: dict[str, Any], seed: int | None) -> dict[str, Any]:
    avatar_path = root / row.get("person", row["images"][0])
    garment_path = root / row.get("garment", row["images"][1])
    with avatar_path.open("rb") as avatar_f, garment_path.open("rb") as garment_f:
        files = {
            "avatar": (avatar_path.name, avatar_f, "image/png"),
            "garment": (garment_path.name, garment_f, "image/png"),
        }
        data = {"category": row.get("category", "top")}
        if seed is not None:
            data["seed"] = str(seed)
        r = client.post(f"{base_url}/try-on", data=data, files=files, timeout=None)
    r.raise_for_status()
    return r.json()


def post_ghost(client: httpx.Client, base_url: str, root: Path, row: dict[str, Any], seed: int | None, steps: int | None) -> dict[str, Any]:
    input_path = root / row.get("input", row["images"][0])
    with input_path.open("rb") as image_f:
        files = {"image": (input_path.name, image_f, "image/png")}
        data = {"category": row.get("category", "top")}
        if seed is not None:
            data["seed"] = str(seed)
        if steps is not None:
            data["steps"] = str(steps)
        r = client.post(f"{base_url}/ghost-mannequin", data=data, files=files, timeout=None)
    r.raise_for_status()
    return r.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--endpoint", choices=["try-on", "ghost-mannequin"], required=True)
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--out", default="runs/eval_proto")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--steps", type=int, default=None, help="Only applies to ghost endpoint; try-on uses service config")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.dataset_root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(Path(args.manifest))[: args.limit]
    if not rows:
        raise SystemExit("No manifest rows found")

    metrics: list[dict[str, Any]] = []

    with httpx.Client() as client:
        health = client.get(f"{args.base_url}/health", timeout=15).json()
        print("Health:", json.dumps(health, indent=2))

        for i, row in enumerate(rows):
            print(f"[{i + 1}/{len(rows)}] {args.endpoint} sample={row['id']}")
            start = time.time()
            if args.endpoint == "try-on":
                result = post_tryon(client, args.base_url, root, row, seed=args.seed + i if args.seed is not None else None)
            else:
                result = post_ghost(client, args.base_url, root, row, seed=args.seed + i if args.seed is not None else None, steps=args.steps)
            wall_ms = int((time.time() - start) * 1000)

            metric = {
                "id": row["id"],
                "success": result.get("success", False),
                "service_processing_time_ms": result.get("processing_time_ms"),
                "wall_time_ms": wall_ms,
                "seed_used": result.get("seed_used"),
                "error": result.get("error"),
            }
            metrics.append(metric)

            if result.get("success") and result.get("image_base64"):
                save_base64_png(result["image_base64"], out / f"{args.endpoint}_{row['id']}.png")
            else:
                print("  ERROR:", result.get("error"))

    summary = {
        "endpoint": args.endpoint,
        "base_url": args.base_url,
        "count": len(metrics),
        "success_count": sum(1 for m in metrics if m["success"]),
        "avg_service_processing_time_ms": mean([m["service_processing_time_ms"] for m in metrics if m.get("service_processing_time_ms") is not None]) if metrics else None,
        "avg_wall_time_ms": mean([m["wall_time_ms"] for m in metrics]) if metrics else None,
        "items": metrics,
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nSummary:", json.dumps(summary, indent=2))
    print(f"Saved outputs to {out}")


if __name__ == "__main__":
    main()
