#!/usr/bin/env python3
"""Download a small multi-identity face dataset (LFW) for identity-consistency eval.

Note: LFW is mostly face/portrait crops, not full-body fashion poses.
Use this as a quick identity-preservation benchmark, not as final avatar-production data.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out-root", default="training/benchmarks/assets/identity_people_lfw")
    p.add_argument("--min-faces-per-person", type=int, default=20)
    p.add_argument("--max-identities", type=int, default=10)
    p.add_argument("--max-images-per-identity", type=int, default=8)
    p.add_argument("--resize", type=float, default=1.0, help="Scale factor passed to fetch_lfw_people")
    p.add_argument("--full-image", action="store_true", help="Use full uncropped LFW frames (better resolution/context)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    try:
        from sklearn.datasets import fetch_lfw_people
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "scikit-learn is required. Install with: pip install scikit-learn\n"
            f"Import error: {exc}"
        )

    out_root = Path(args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    fetch_kwargs = {
        "min_faces_per_person": args.min_faces_per_person,
        "resize": args.resize,
        "color": True,
    }
    if args.full_image:
        fetch_kwargs["slice_"] = None
    ds = fetch_lfw_people(**fetch_kwargs)

    # ds.images shape: (N, H, W, 3)
    by_label: dict[int, list[int]] = {}
    for i, y in enumerate(ds.target.tolist()):
        by_label.setdefault(int(y), []).append(i)

    # Sort identities by number of images desc
    labels_sorted = sorted(by_label.keys(), key=lambda y: len(by_label[y]), reverse=True)
    labels_sorted = labels_sorted[: args.max_identities]

    saved = 0
    for y in labels_sorted:
        name = ds.target_names[y].replace(" ", "_")
        indices = by_label[y][: args.max_images_per_identity]
        ident_dir = out_root / name
        ident_dir.mkdir(parents=True, exist_ok=True)
        for j, idx in enumerate(indices, start=1):
            arr = ds.images[idx]
            # sklearn LFW returns float32 in [0, 1]; convert safely to 8-bit RGB.
            if arr.dtype.kind == "f":
                arr = arr * (255.0 if float(arr.max()) <= 1.0 else 1.0)
            arr = arr.clip(0, 255).astype("uint8")
            img = Image.fromarray(arr, mode="RGB")
            path = ident_dir / f"{j:04d}.jpg"
            img.save(path, quality=95)
            saved += 1

    print(f"Saved {saved} images in {out_root}")
    print(f"Settings: resize={args.resize}, full_image={args.full_image}")
    print("Identities:")
    for y in labels_sorted:
        name = ds.target_names[y].replace(" ", "_")
        count = min(len(by_label[y]), args.max_images_per_identity)
        print(f"  - {name}: {count}")


if __name__ == "__main__":
    main()
