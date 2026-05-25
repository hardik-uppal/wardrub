#!/usr/bin/env python3
"""Run benchmark manifest against image-edit-service endpoints.

Supports mixed endpoint manifests (`ghost-mannequin`, `try-on`, `edit`) and saves
outputs + per-sample response JSON for later scoring.
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


def resolve_path(dataset_root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (dataset_root / p)


def save_base64_png(image_b64: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(image_b64))


def post_ghost(
    client: httpx.Client,
    base_url: str,
    root: Path,
    row: dict[str, Any],
    seed_override: int | None,
) -> dict[str, Any]:
    image_path = resolve_path(root, row["image"])
    files: dict[str, tuple[str, Any, str]] = {}
    data: dict[str, str] = {"category": str(row.get("category", "top"))}

    if row.get("custom_prompt"):
        data["custom_prompt"] = str(row["custom_prompt"])
    if row.get("steps") is not None:
        data["steps"] = str(row["steps"])

    seed = seed_override if seed_override is not None else row.get("seed")
    if seed is not None:
        data["seed"] = str(seed)

    with image_path.open("rb") as front_f:
        files["image"] = (image_path.name, front_f, "image/png")
        if row.get("back_image"):
            back_path = resolve_path(root, row["back_image"])
            with back_path.open("rb") as back_f:
                files["back_image"] = (back_path.name, back_f, "image/png")
                r = client.post(f"{base_url}/ghost-mannequin", data=data, files=files, timeout=None)
        else:
            r = client.post(f"{base_url}/ghost-mannequin", data=data, files=files, timeout=None)

    r.raise_for_status()
    return r.json()


def post_tryon(
    client: httpx.Client,
    base_url: str,
    root: Path,
    row: dict[str, Any],
    seed_override: int | None,
) -> dict[str, Any]:
    avatar_path = resolve_path(root, row["avatar"])
    garment_path = resolve_path(root, row["garment"])

    data = {"category": str(row.get("category", "top"))}
    seed = seed_override if seed_override is not None else row.get("seed")
    if seed is not None:
        data["seed"] = str(seed)

    with avatar_path.open("rb") as avatar_f, garment_path.open("rb") as garment_f:
        files = {
            "avatar": (avatar_path.name, avatar_f, "image/png"),
            "garment": (garment_path.name, garment_f, "image/png"),
        }
        r = client.post(f"{base_url}/try-on", data=data, files=files, timeout=None)

    r.raise_for_status()
    return r.json()


def post_edit(
    client: httpx.Client,
    base_url: str,
    root: Path,
    row: dict[str, Any],
    seed_override: int | None,
) -> dict[str, Any]:
    image_path = resolve_path(root, row["image"])
    data = {"prompt": str(row["prompt"]) }

    if row.get("steps") is not None:
        data["steps"] = str(row["steps"])

    seed = seed_override if seed_override is not None else row.get("seed")
    if seed is not None:
        data["seed"] = str(seed)

    with image_path.open("rb") as image_f:
        files = {"image": (image_path.name, image_f, "image/png")}
        r = client.post(f"{base_url}/edit", data=data, files=files, timeout=None)

    r.raise_for_status()
    return r.json()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--dataset-root", default=".")
    p.add_argument("--base-url", default="http://localhost:8001")
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=0, help="0 means all rows")
    p.add_argument("--seed-start", type=int, default=None, help="If set, overrides per-row seed as seed-start+i")
    p.add_argument("--endpoint", choices=["ghost-mannequin", "try-on", "edit"], default=None, help="Force endpoint for all rows")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    manifest = Path(args.manifest).resolve()
    root = Path(args.dataset_root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(manifest)
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("No rows to run")

    metrics: list[dict[str, Any]] = []

    with httpx.Client() as client:
        health = client.get(f"{args.base_url}/health", timeout=20).json()
        print("Health:", json.dumps(health, indent=2))

        for i, row in enumerate(rows):
            endpoint = args.endpoint or row.get("endpoint")
            if endpoint not in {"ghost-mannequin", "try-on", "edit"}:
                print(f"[skip] id={row.get('id')} invalid endpoint={endpoint}")
                continue

            rid = str(row.get("id", f"row_{i:05d}"))
            seed_override = args.seed_start + i if args.seed_start is not None else None

            print(f"[{i+1}/{len(rows)}] endpoint={endpoint} id={rid}")
            start = time.time()
            try:
                if endpoint == "ghost-mannequin":
                    result = post_ghost(client, args.base_url, root, row, seed_override)
                elif endpoint == "try-on":
                    result = post_tryon(client, args.base_url, root, row, seed_override)
                else:
                    result = post_edit(client, args.base_url, root, row, seed_override)
            except Exception as exc:
                result = {"success": False, "error": str(exc)}

            wall_ms = int((time.time() - start) * 1000)
            sample_out = out / endpoint / rid
            sample_out.parent.mkdir(parents=True, exist_ok=True)

            if result.get("success") and result.get("image_base64"):
                save_base64_png(result["image_base64"], sample_out.with_suffix(".png"))

            response_record = {
                "manifest_row": row,
                "endpoint": endpoint,
                "result": result,
                "wall_time_ms": wall_ms,
                "timestamp": int(time.time()),
            }
            sample_out.with_suffix(".response.json").write_text(
                json.dumps(response_record, indent=2), encoding="utf-8"
            )

            metric = {
                "id": rid,
                "endpoint": endpoint,
                "success": bool(result.get("success", False)),
                "service_processing_time_ms": result.get("processing_time_ms"),
                "wall_time_ms": wall_ms,
                "seed_used": result.get("seed_used"),
                "error": result.get("error"),
                "output_image": str(sample_out.with_suffix(".png")) if result.get("success") else None,
            }
            metrics.append(metric)

    by_ep: dict[str, list[dict[str, Any]]] = {}
    for m in metrics:
        by_ep.setdefault(m["endpoint"], []).append(m)

    endpoint_summary = {}
    for endpoint, items in by_ep.items():
        endpoint_summary[endpoint] = {
            "count": len(items),
            "success_count": sum(1 for x in items if x["success"]),
            "avg_service_processing_time_ms": mean(
                [x["service_processing_time_ms"] for x in items if x.get("service_processing_time_ms") is not None]
            ) if items else None,
            "avg_wall_time_ms": mean([x["wall_time_ms"] for x in items]) if items else None,
        }

    summary = {
        "manifest": str(manifest),
        "dataset_root": str(root),
        "base_url": args.base_url,
        "count": len(metrics),
        "success_count": sum(1 for m in metrics if m["success"]),
        "endpoint_summary": endpoint_summary,
        "items": metrics,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nSummary:", json.dumps(summary, indent=2))
    print(f"Saved outputs to {out}")


if __name__ == "__main__":
    main()
