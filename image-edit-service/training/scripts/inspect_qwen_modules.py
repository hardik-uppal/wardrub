#!/usr/bin/env python3
"""Inspect Qwen-Image-Edit transformer modules to choose LoRA target modules.

Run locally before implementing/launching a full LoRA training run:

  python training/scripts/inspect_qwen_modules.py --max-lines 300

This intentionally only prints module names/shapes; it does not modify weights.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="toandev/Qwen-Image-Edit-2511-4bit")
    parser.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "huggingface"))
    parser.add_argument("--max-lines", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from diffusers import QwenImageEditPlusPipeline

    pipe = QwenImageEditPlusPipeline.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
        cache_dir=args.cache_dir,
    )
    transformer = pipe.transformer

    suffix_counts: Counter[str] = Counter()
    linear_like = []
    for name, module in transformer.named_modules():
        suffix_counts[name.split(".")[-1]] += 1
        cls = module.__class__.__name__.lower()
        if "linear" in cls or "lora" in cls:
            shape = None
            if hasattr(module, "weight") and getattr(module, "weight") is not None:
                try:
                    shape = tuple(module.weight.shape)
                except Exception:
                    shape = None
            linear_like.append((name, module.__class__.__name__, shape))

    print("Top module suffixes:")
    for suffix, count in suffix_counts.most_common(80):
        print(f"  {suffix}: {count}")

    print("\nLinear-like modules:")
    for name, cls, shape in linear_like[: args.max_lines]:
        print(f"  {name} [{cls}] shape={shape}")
    if len(linear_like) > args.max_lines:
        print(f"  ... {len(linear_like) - args.max_lines} more")

    candidates = ["to_q", "to_k", "to_v", "to_out.0", "proj", "proj_out", "ff", "w1", "w2", "w3"]
    print("\nCandidate target-module hits:")
    for candidate in candidates:
        hits = [name for name, _, _ in linear_like if name.endswith(candidate) or f".{candidate}." in name]
        print(f"  {candidate}: {len(hits)}")


if __name__ == "__main__":
    main()
