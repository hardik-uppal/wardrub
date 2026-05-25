#!/usr/bin/env python3
"""Smoke-test Qwen pipeline LoRA adapter loading for Wardrub.

This does not train. It validates that the local image-edit-service can load:
1. the existing Qwen Lightning LoRA, and
2. an optional Wardrub LoRA path,
then combine adapters via `set_adapters` when supported by Diffusers.

Use before a long RunPod training run to catch adapter/API issues locally.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="toandev/Qwen-Image-Edit-2511-4bit")
    parser.add_argument("--lightning-repo", default="lightx2v/Qwen-Image-Edit-2511-Lightning")
    parser.add_argument("--lightning-weight", default="Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors")
    parser.add_argument("--wardrub-lora-path", default=None)
    parser.add_argument("--wardrub-lora-weight-name", default=None)
    parser.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "huggingface"))
    parser.add_argument("--cpu-offload", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from diffusers import QwenImageEditPlusPipeline

    print(f"Loading model: {args.model_id}")
    pipe = QwenImageEditPlusPipeline.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
        cache_dir=args.cache_dir,
    )

    adapters: list[str] = []
    weights: list[float] = []

    print("Loading Lightning LoRA")
    pipe.load_lora_weights(
        args.lightning_repo,
        weight_name=args.lightning_weight,
        adapter_name="lightning",
        cache_dir=args.cache_dir,
    )
    adapters.append("lightning")
    weights.append(1.0)

    if args.wardrub_lora_path:
        print(f"Loading Wardrub LoRA: {args.wardrub_lora_path}")
        kwargs = {"adapter_name": "wardrub"}
        if args.wardrub_lora_weight_name:
            kwargs["weight_name"] = args.wardrub_lora_weight_name
        pipe.load_lora_weights(args.wardrub_lora_path, **kwargs)
        adapters.append("wardrub")
        weights.append(0.75)

    if hasattr(pipe, "set_adapters"):
        print(f"Combining adapters: {adapters} weights={weights}")
        pipe.set_adapters(adapters, adapter_weights=weights)
    else:
        print("WARNING: pipeline does not expose set_adapters(); only last-loaded adapter may apply")

    if args.cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")

    print("OK: adapter stack loaded")
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        print(f"GPU memory: allocated={allocated:.2f}GB reserved={reserved:.2f}GB")


if __name__ == "__main__":
    main()
