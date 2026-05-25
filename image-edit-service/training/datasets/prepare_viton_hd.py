#!/usr/bin/env python3
"""Prepare a small VITON-HD prototype dataset for Wardrub VTON/ghost experiments.

The script downloads/loads `forgeml/viton_hd` via Hugging Face Datasets and exports
plain image files plus JSONL manifests that are easy to use from the local image
service, LoRA experiments, or RunPod.

Exported structure:

  <output>/
    train/
      persons/000000.png        # garment-agnostic person / avatar conditioning
      garments/000000.png       # flat-lay garment conditioning
      targets/000000.png        # person wearing garment, ground truth
      garment_masks/000000.png  # optional garment mask from dataset
      poses/000000.png          # optional pose image from dataset
    manifests/
      tryon_train.jsonl         # persons + garments -> targets
      ghost_train.jsonl         # targets/person-wearing-garment -> garments
      samples_debug_grid.jpg

For local 4090 debugging, start with --max-samples 32 or 64.
For RunPod, raise --max-samples or omit it to export the full split.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps
from tqdm import tqdm


TRYON_PROMPT = (
    "Virtual try-on: dress the person in the provided garment. Preserve the "
    "person's pose, face, body shape, lighting, and background. Preserve the exact "
    "garment texture, color, print, logo, collar, sleeves, and silhouette. Produce "
    "a photorealistic fashion image."
)

GHOST_PROMPT = (
    "Create a clean professional e-commerce ghost mannequin / flat product photo "
    "of only the garment from this person image. Remove the person completely. "
    "Preserve exact fabric, seams, color, print, collar, sleeves, and silhouette. "
    "Use a pure white background."
)


def pil_image(value: Any) -> Image.Image | None:
    """Convert a HF dataset image cell to RGB PIL image."""
    if value is None:
        return None
    if isinstance(value, Image.Image):
        return ImageOps.exif_transpose(value).convert("RGB")
    if isinstance(value, dict) and "path" in value and value["path"]:
        return ImageOps.exif_transpose(Image.open(value["path"])).convert("RGB")
    if isinstance(value, (str, Path)):
        return ImageOps.exif_transpose(Image.open(value)).convert("RGB")
    raise TypeError(f"Unsupported image value: {type(value)!r}")


def resize_if_requested(img: Image.Image, size: tuple[int, int] | None) -> Image.Image:
    if size is None:
        return img
    return img.resize(size, Image.Resampling.LANCZOS)


def save_image(img: Image.Image | None, path: Path) -> str | None:
    if img is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)
    return str(path)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_debug_grid(output_root: Path, rows: list[dict[str, Any]], limit: int = 24) -> None:
    if not rows:
        return

    thumb_w, thumb_h = 180, 240
    cols = 3
    pad = 16
    label_h = 24
    n = min(limit, len(rows))
    grid = Image.new(
        "RGB",
        (cols * thumb_w + (cols + 1) * pad, n * (thumb_h + label_h) + (n + 1) * pad),
        "white",
    )
    draw = ImageDraw.Draw(grid)

    for i, row in enumerate(rows[:n]):
        image_paths = [Path(output_root / p) for p in row["images"]]
        target_path = Path(output_root / row["target"])
        panels = image_paths[:2] + [target_path]
        labels = ["person", "garment", "target"] if row["task"] == "try_on" else ["input", "", "target"]

        y = pad + i * (thumb_h + label_h + pad)
        for j, panel_path in enumerate(panels[:cols]):
            x = pad + j * (thumb_w + pad)
            if panel_path.exists():
                img = Image.open(panel_path).convert("RGB")
                img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (thumb_w, thumb_h), "#f5f5f5")
                canvas.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
                grid.paste(canvas, (x, y + label_h))
            draw.text((x, y), labels[j] if j < len(labels) else "", fill="black")

    out = output_root / "manifests" / "samples_debug_grid.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    grid.save(out, quality=92)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="forgeml/viton_hd", help="HF dataset id")
    parser.add_argument("--split", default="train", help="Dataset split")
    parser.add_argument("--output", default="data/viton_hd_proto", help="Output directory")
    parser.add_argument("--max-samples", type=int, default=64, help="Limit for local prototype; use 0 for full split")
    parser.add_argument("--streaming", action="store_true", help="Stream from HF instead of loading Arrow cache")
    parser.add_argument("--resize", action="store_true", help="Resize all images to --width/--height")
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--debug-grid-limit", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from datasets import load_dataset

    output_root = Path(args.output).resolve()
    train_root = output_root / "train"
    manifests_root = output_root / "manifests"
    output_root.mkdir(parents=True, exist_ok=True)

    split = args.split if args.max_samples == 0 else f"{args.split}[:{args.max_samples}]"
    print(f"Loading {args.dataset} split={split} streaming={args.streaming}")
    ds = load_dataset(args.dataset, split=split, streaming=args.streaming)

    resize_to = (args.width, args.height) if args.resize else None

    tryon_rows: list[dict[str, Any]] = []
    ghost_rows: list[dict[str, Any]] = []

    iterator = ds if args.streaming else iter(ds)
    total = None if args.streaming else len(ds)  # type: ignore[arg-type]

    for idx, sample in enumerate(tqdm(iterator, total=total, desc="Exporting VITON-HD")):
        if args.streaming and args.max_samples and idx >= args.max_samples:
            break

        sample_id = f"{idx:06d}"
        person = resize_if_requested(pil_image(sample.get("agnostic")), resize_to)
        garment = resize_if_requested(pil_image(sample.get("cloth")), resize_to)
        target = resize_if_requested(pil_image(sample.get("image")), resize_to)
        garment_mask = resize_if_requested(pil_image(sample.get("cloth_mask")), resize_to)
        pose = resize_if_requested(pil_image(sample.get("pose")), resize_to)
        caption = sample.get("caption") or ""

        person_path = train_root / "persons" / f"{sample_id}.png"
        garment_path = train_root / "garments" / f"{sample_id}.png"
        target_path = train_root / "targets" / f"{sample_id}.png"
        mask_path = train_root / "garment_masks" / f"{sample_id}.png"
        pose_path = train_root / "poses" / f"{sample_id}.png"

        save_image(person, person_path)
        save_image(garment, garment_path)
        save_image(target, target_path)
        save_image(garment_mask, mask_path)
        save_image(pose, pose_path)

        tryon_rows.append(
            {
                "id": sample_id,
                "task": "try_on",
                "category": "top",
                "images": [rel(person_path, output_root), rel(garment_path, output_root)],
                "person": rel(person_path, output_root),
                "garment": rel(garment_path, output_root),
                "target": rel(target_path, output_root),
                "pose": rel(pose_path, output_root),
                "garment_mask": rel(mask_path, output_root),
                "prompt": TRYON_PROMPT,
                "caption": caption,
                "source_dataset": args.dataset,
            }
        )

        ghost_rows.append(
            {
                "id": sample_id,
                "task": "ghost_mannequin",
                "category": "top",
                "images": [rel(target_path, output_root)],
                "input": rel(target_path, output_root),
                "target": rel(garment_path, output_root),
                "garment_mask": rel(mask_path, output_root),
                "prompt": GHOST_PROMPT,
                "caption": caption,
                "source_dataset": args.dataset,
            }
        )

    write_jsonl(manifests_root / "tryon_train.jsonl", tryon_rows)
    write_jsonl(manifests_root / "ghost_train.jsonl", ghost_rows)
    write_jsonl(manifests_root / "mixed_train.jsonl", tryon_rows + ghost_rows)
    make_debug_grid(output_root, tryon_rows, limit=args.debug_grid_limit)

    print("\nDone.")
    print(f"Output: {output_root}")
    print(f"Try-on manifest: {manifests_root / 'tryon_train.jsonl'} ({len(tryon_rows)} rows)")
    print(f"Ghost manifest: {manifests_root / 'ghost_train.jsonl'} ({len(ghost_rows)} rows)")
    print(f"Debug grid: {manifests_root / 'samples_debug_grid.jpg'}")


if __name__ == "__main__":
    main()
