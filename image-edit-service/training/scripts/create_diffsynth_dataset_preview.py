#!/usr/bin/env python3
"""Create local/WandB visual previews for a DiffSynth image-edit dataset.

For Wardrub VTON, this creates per-row panels with edit/input images and target image,
plus a contact sheet. It is intentionally lightweight and safe to run before training.
"""
from __future__ import annotations

import argparse
import json
import os
import textwrap
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        return json.loads(text)
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _open_image(base: Path, rel: str, size: tuple[int, int]) -> Image.Image:
    path = base / rel
    img = Image.open(path).convert("RGB")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def _draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str) -> None:
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text(xy, label, fill=(0, 0, 0), font=font)


def _panel_for_row(base: Path, row: dict, idx: int, thumb: tuple[int, int]) -> Image.Image:
    edit_images = row.get("edit_image", [])
    if isinstance(edit_images, str):
        edit_images = [edit_images]
    columns: list[tuple[str, str]] = []
    for j, rel in enumerate(edit_images):
        columns.append((f"edit_{j}", rel))
    if row.get("image"):
        columns.append(("target", row["image"]))
    if not columns:
        columns = [("missing", "")]

    label_h = 26
    prompt_h = 58
    margin = 8
    width = len(columns) * thumb[0] + (len(columns) + 1) * margin
    height = label_h + thumb[1] + prompt_h + margin * 3
    panel = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(panel)
    _draw_label(draw, (margin, 4), f"sample {idx:06d}")

    for c, (label, rel) in enumerate(columns):
        x = margin + c * (thumb[0] + margin)
        y = label_h
        if rel:
            try:
                img = _open_image(base, rel, thumb)
            except Exception as exc:
                img = Image.new("RGB", thumb, (255, 220, 220))
                ImageDraw.Draw(img).text((6, 6), f"ERR\n{rel}\n{exc}", fill=(0, 0, 0))
        else:
            img = Image.new("RGB", thumb, (240, 240, 240))
        panel.paste(img, (x, y))
        _draw_label(draw, (x, y + thumb[1] + 2), label)

    prompt = str(row.get("prompt", ""))
    prompt = "\n".join(textwrap.wrap(prompt, width=max(40, width // 8))[:3])
    draw.text((margin, label_h + thumb[1] + 20), prompt, fill=(40, 40, 40))
    return panel


def _make_contact_sheet(images: Iterable[Image.Image], cols: int = 2, bg: str = "white") -> Image.Image:
    imgs = list(images)
    if not imgs:
        return Image.new("RGB", (512, 256), bg)
    cell_w = max(i.width for i in imgs)
    cell_h = max(i.height for i in imgs)
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), bg)
    for idx, img in enumerate(imgs):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        sheet.paste(img, (x, y))
    return sheet


def _maybe_log_wandb(out_dir: Path, panels: list[Path], contact_sheet: Path, args: argparse.Namespace) -> None:
    wandb_enabled = _truthy(os.environ.get("WARDRUB_ENABLE_WANDB")) or (
        os.environ.get("WARDRUB_ENABLE_WANDB", "auto").lower() == "auto" and bool(os.environ.get("WANDB_API_KEY"))
    )
    if not wandb_enabled:
        return
    try:
        import wandb

        run = wandb.init(
            project=os.environ.get("WANDB_PROJECT", "wardrub-vton-lora"),
            entity=os.environ.get("WANDB_ENTITY") or None,
            name=os.environ.get("WANDB_RUN_NAME") or os.environ.get("WARDRUB_RUN_ID") or "wardrub-preview",
            group=os.environ.get("WANDB_RUN_GROUP") or "runpod-smoke",
            id=os.environ.get("WANDB_RUN_ID") or os.environ.get("WARDRUB_RUN_ID") or None,
            resume=os.environ.get("WANDB_RESUME", "allow"),
            dir=str(out_dir),
            config={
                "dataset_base_path": str(args.dataset_base_path),
                "metadata_path": str(args.metadata_path),
                "preview_rows": args.max_rows,
            },
        )
        run.log({
            "dataset/contact_sheet": wandb.Image(str(contact_sheet)),
            "dataset/previews": [wandb.Image(str(p)) for p in panels],
        }, step=0)
        run.finish()
        print(f"Logged dataset previews to WandB run id={os.environ.get('WANDB_RUN_ID') or os.environ.get('WARDRUB_RUN_ID')}")
    except Exception as exc:
        print(f"WandB preview logging skipped: {exc!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-base-path", type=Path, required=True)
    parser.add_argument("--metadata-path", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-rows", type=int, default=8)
    parser.add_argument("--thumb-width", type=int, default=224)
    parser.add_argument("--thumb-height", type=int, default=300)
    parser.add_argument("--contact-cols", type=int, default=2)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = _load_rows(args.metadata_path)[: args.max_rows]
    panels = []
    panel_paths = []
    thumb = (args.thumb_width, args.thumb_height)
    for idx, row in enumerate(rows):
        panel = _panel_for_row(args.dataset_base_path, row, idx, thumb)
        path = args.out_dir / f"preview_{idx:06d}.jpg"
        panel.save(path, quality=92)
        panels.append(panel)
        panel_paths.append(path)

    contact = _make_contact_sheet(panels, cols=args.contact_cols)
    contact_path = args.out_dir / "contact_sheet.jpg"
    contact.save(contact_path, quality=92)

    manifest = {
        "dataset_base_path": str(args.dataset_base_path),
        "metadata_path": str(args.metadata_path),
        "rows_previewed": len(rows),
        "contact_sheet": str(contact_path),
        "panels": [str(p) for p in panel_paths],
    }
    (args.out_dir / "preview_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    _maybe_log_wandb(args.out_dir, panel_paths, contact_path, args)


if __name__ == "__main__":
    main()
