#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VALID_ENDPOINTS = {"ghost-mannequin", "try-on", "edit"}
VALID_CATEGORIES = {"top", "bottom", "dress", "outerwear"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{i} invalid JSON: {exc}")
    return rows


def resolve_path(dataset_root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (dataset_root / p)


def validate_row(row: dict[str, Any], dataset_root: Path, check_paths: bool) -> list[str]:
    errors: list[str] = []

    rid = row.get("id")
    if not rid or not isinstance(rid, str):
        errors.append("missing/invalid id")

    endpoint = row.get("endpoint")
    if endpoint not in VALID_ENDPOINTS:
        errors.append(f"invalid endpoint={endpoint!r}")
        return errors

    category = row.get("category")
    if category is not None and category not in VALID_CATEGORIES:
        errors.append(f"invalid category={category!r}")

    def require_path(key: str) -> None:
        val = row.get(key)
        if not isinstance(val, str) or not val:
            errors.append(f"missing {key}")
            return
        if check_paths:
            p = resolve_path(dataset_root, val)
            if not p.exists():
                errors.append(f"path not found for {key}: {val}")

    if endpoint == "ghost-mannequin":
        require_path("image")
        if "back_image" in row and isinstance(row["back_image"], str) and check_paths:
            p = resolve_path(dataset_root, row["back_image"])
            if not p.exists():
                errors.append(f"path not found for back_image: {row['back_image']}")

    elif endpoint == "try-on":
        require_path("avatar")
        require_path("garment")

    elif endpoint == "edit":
        require_path("image")
        prompt = row.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append("missing prompt")

    return errors


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--dataset-root", default=".")
    p.add_argument("--no-path-check", action="store_true", help="Validate schema only")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    manifest = Path(args.manifest).resolve()
    dataset_root = Path(args.dataset_root).resolve()

    rows = read_jsonl(manifest)
    if not rows:
        raise SystemExit(f"No rows found in {manifest}")

    seen = set()
    total_errors = 0
    for i, row in enumerate(rows, start=1):
        rid = row.get("id")
        if rid in seen:
            print(f"[row {i}] duplicate id={rid}")
            total_errors += 1
        seen.add(rid)

        errs = validate_row(row, dataset_root, check_paths=not args.no_path_check)
        if errs:
            total_errors += len(errs)
            print(f"[row {i} id={rid}]")
            for e in errs:
                print(f"  - {e}")

    if total_errors:
        raise SystemExit(f"Validation failed: {total_errors} issue(s)")

    print(f"OK: {len(rows)} rows validated in {manifest}")


if __name__ == "__main__":
    main()
