#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--assets-root", default="training/benchmarks/assets/identity_people")
    p.add_argument("--out", default="training/benchmarks/avatar_identity_v1.jsonl")
    p.add_argument("--steps", type=int, default=30)
    p.add_argument(
        "--prompt-mode",
        choices=["full_body_neutral", "portrait_neutral"],
        default="full_body_neutral",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    assets = Path(args.assets_root).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if not assets.exists():
        raise SystemExit(f"assets root not found: {assets}")

    if args.prompt_mode == "portrait_neutral":
        prompt = "Create a clean neutral portrait avatar on plain background. Preserve exact facial identity, skin tone, and facial features with high clarity."
    else:
        prompt = "Create a full-body neutral standing avatar (front-facing, arms relaxed) on a plain background. Preserve exact facial identity, skin tone, body proportions, and key appearance details."

    rows = []
    for ident_dir in sorted([p for p in assets.iterdir() if p.is_dir()]):
        identity = ident_dir.name
        imgs = sorted(
            [p for p in ident_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        )
        for i, img in enumerate(imgs, start=1):
            rid = f"id_{identity}_{i:04d}"
            rel = img.relative_to(Path.cwd()).as_posix()
            rows.append(
                {
                    "id": rid,
                    "endpoint": "edit",
                    "image": rel,
                    "prompt": prompt,
                    "steps": args.steps,
                    "tags": {
                        "identity": identity,
                        "split": "eval",
                    },
                }
            )

    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows -> {out}")
    print(f"prompt_mode={args.prompt_mode}")


if __name__ == "__main__":
    main()
