#!/usr/bin/env python3
"""Build local benchmark sets from existing viton_hd_proto assets.

Creates benchmark asset folders + ready-to-run manifests so we can evaluate
without downloading new data or using RunPod.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def copy_rel(src_root: Path, rel: str, dst: Path) -> str:
    src = src_root / rel
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.as_posix()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--viton-manifest", default="data/viton_hd_proto/manifests/tryon_train.jsonl")
    p.add_argument("--viton-root", default="data/viton_hd_proto")
    p.add_argument("--ghost-count", type=int, default=24)
    p.add_argument("--look-count", type=int, default=24)
    p.add_argument("--avatar-count", type=int, default=24)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.repo_root).resolve()

    viton_manifest = (root / args.viton_manifest).resolve()
    viton_root = (root / args.viton_root).resolve()

    rows = read_jsonl(viton_manifest)
    if not rows:
        raise SystemExit(f"No rows in {viton_manifest}")

    rng = random.Random(args.seed)

    ghost_n = min(args.ghost_count, len(rows))
    look_n = min(args.look_count, len(rows))
    avatar_n = min(args.avatar_count, len(rows))

    ghost_rows = rng.sample(rows, ghost_n)
    look_rows = rng.sample(rows, look_n)
    avatar_rows = rng.sample(rows, avatar_n)

    bench_dir = root / "training" / "benchmarks"
    assets = bench_dir / "assets" / "v1"

    ghost_person_dir = assets / "ghost_inputs" / "person"
    ghost_flatlay_dir = assets / "ghost_inputs" / "flatlay"
    look_avatar_dir = assets / "look_inputs" / "avatar"
    look_garment_dir = assets / "look_inputs" / "garment"
    avatar_input_dir = assets / "avatar_inputs"

    for d in [ghost_person_dir, ghost_flatlay_dir, look_avatar_dir, look_garment_dir, avatar_input_dir]:
        d.mkdir(parents=True, exist_ok=True)

    ghost_manifest: list[dict[str, Any]] = []
    for i, r in enumerate(ghost_rows):
        sid = str(r["id"])

        # Person-wearing input case (harder cleanup)
        dst_person = ghost_person_dir / f"{sid}_person.png"
        rel_person = copy_rel(viton_root, r["target"], dst_person).replace(str(root) + "/", "")
        ghost_manifest.append(
            {
                "id": f"ghost_person_{i:04d}",
                "endpoint": "ghost-mannequin",
                "image": rel_person,
                "category": r.get("category", "top"),
                "custom_prompt": "Remove the person completely and keep only the garment as a clean ghost mannequin product image on pure white background.",
                "tags": {
                    "source_type": "person",
                    "difficulty": "hard",
                    "split": "eval",
                    "origin": "viton_hd_proto",
                },
            }
        )

        # Flatlay/garment-only input case (easier)
        dst_flat = ghost_flatlay_dir / f"{sid}_garment.png"
        rel_flat = copy_rel(viton_root, r["garment"], dst_flat).replace(str(root) + "/", "")
        ghost_manifest.append(
            {
                "id": f"ghost_flatlay_{i:04d}",
                "endpoint": "ghost-mannequin",
                "image": rel_flat,
                "category": r.get("category", "top"),
                "custom_prompt": "Create a professional ghost mannequin style product shot on pure white background, preserving exact fabric details.",
                "tags": {
                    "source_type": "flatlay",
                    "difficulty": "medium",
                    "split": "eval",
                    "origin": "viton_hd_proto",
                },
            }
        )

    # include current local sample if present
    extra_garment = root / "test_images" / "garment_top.png"
    if extra_garment.exists():
        dst_extra = ghost_flatlay_dir / "extra_garment_top.png"
        shutil.copy2(extra_garment, dst_extra)
        rel_extra = dst_extra.as_posix().replace(str(root) + "/", "")
        ghost_manifest.append(
            {
                "id": "ghost_extra_0000",
                "endpoint": "ghost-mannequin",
                "image": rel_extra,
                "category": "top",
                "custom_prompt": "Generate a clean ghost mannequin garment image on white background with catalog quality lighting.",
                "tags": {
                    "source_type": "flatlay_like",
                    "difficulty": "easy",
                    "split": "eval",
                    "origin": "local_test_images",
                },
            }
        )

    look_manifest: list[dict[str, Any]] = []
    for i, r in enumerate(look_rows):
        sid = str(r["id"])
        dst_avatar = look_avatar_dir / f"{sid}_avatar.png"
        dst_garment = look_garment_dir / f"{sid}_garment.png"
        rel_avatar = copy_rel(viton_root, r["person"], dst_avatar).replace(str(root) + "/", "")
        rel_garment = copy_rel(viton_root, r["garment"], dst_garment).replace(str(root) + "/", "")
        look_manifest.append(
            {
                "id": f"look_{i:04d}",
                "endpoint": "try-on",
                "avatar": rel_avatar,
                "garment": rel_garment,
                "category": r.get("category", "top"),
                "tags": {
                    "source_type": "avatar_plus_garment",
                    "difficulty": "medium",
                    "split": "eval",
                    "origin": "viton_hd_proto",
                },
            }
        )

    avatar_manifest: list[dict[str, Any]] = []
    for i, r in enumerate(avatar_rows):
        sid = str(r["id"])
        dst_avatar = avatar_input_dir / f"{sid}_person.png"
        rel_avatar = copy_rel(viton_root, r["person"], dst_avatar).replace(str(root) + "/", "")
        avatar_manifest.append(
            {
                "id": f"avatar_{i:04d}",
                "endpoint": "edit",
                "image": rel_avatar,
                "prompt": "Create a clean studio avatar portrait with neutral white background, preserving identity, face, and body proportions.",
                "steps": 30,
                "tags": {
                    "source_type": "person_photo",
                    "difficulty": "medium",
                    "split": "eval",
                    "origin": "viton_hd_proto",
                },
            }
        )

    write_jsonl(bench_dir / "ghost_test_v1.jsonl", ghost_manifest)
    write_jsonl(bench_dir / "look_test_v1.jsonl", look_manifest)
    write_jsonl(bench_dir / "avatar_test_v1.jsonl", avatar_manifest)

    print("Built benchmark sets:")
    print(f"  ghost_test_v1.jsonl rows={len(ghost_manifest)}")
    print(f"  look_test_v1.jsonl rows={len(look_manifest)}")
    print(f"  avatar_test_v1.jsonl rows={len(avatar_manifest)}")
    print(f"  assets={assets}")


if __name__ == "__main__":
    main()
