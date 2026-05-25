#!/usr/bin/env python3
"""Smoke-test LoRA gradient flow on the local 4-bit Qwen-Image-Edit-2511 model.

Purpose:
  - Uses the already-cached `toandev/Qwen-Image-Edit-2511-4bit` inference model.
  - Injects PEFT LoRA adapters into the quantized transformer.
  - Runs a tiny synthetic forward/backward through a real target projection module.
  - Verifies LoRA params get non-zero gradients.
  - Saves the adapter to a local smoke output directory.

This is NOT a full diffusion training loop. It is a cheap local sanity check that
QLoRA-style adapter plumbing works before we run full DiffSynth training on RunPod.
"""

from __future__ import annotations

import argparse
import gc
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


DEFAULT_TARGET_MODULES = [
    "to_q",
    "to_k",
    "to_v",
    "to_out.0",
    "add_q_proj",
    "add_k_proj",
    "add_v_proj",
    "to_add_out",
]


def gpu_stats(label: str) -> None:
    if not torch.cuda.is_available():
        print(f"{label}: CUDA unavailable")
        return
    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"{label}: allocated={allocated:.2f}GB reserved={reserved:.2f}GB total={total:.2f}GB")


def trainable_summary(model: torch.nn.Module) -> tuple[int, int]:
    trainable = 0
    total = 0
    for p in model.parameters():
        n = p.numel()
        total += n
        if p.requires_grad:
            trainable += n
    return trainable, total


def find_lora_wrapped_projection(transformer: torch.nn.Module) -> tuple[str, torch.nn.Module]:
    """Find a LoRA-wrapped projection module we can call directly."""
    preferred_suffixes = [
        "transformer_blocks.0.attn.to_q",
        "transformer_blocks.0.attn.to_k",
        "transformer_blocks.0.attn.to_v",
        "transformer_blocks.0.attn.add_q_proj",
    ]
    modules = dict(transformer.named_modules())
    for name in preferred_suffixes:
        if name in modules and hasattr(modules[name], "lora_A"):
            return name, modules[name]
    for name, module in transformer.named_modules():
        if hasattr(module, "lora_A"):
            return name, module
    raise RuntimeError("Could not find any LoRA-wrapped module")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="toandev/Qwen-Image-Edit-2511-4bit")
    parser.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "huggingface"))
    parser.add_argument("--output-dir", default="models/train/wardrub-quantized-lora-gradient-smoke")
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--alpha", type=int, default=16)
    parser.add_argument("--target-modules", default=",".join(DEFAULT_TARGET_MODULES))
    parser.add_argument("--seq-len", type=int, default=8)
    parser.add_argument("--hidden-size", type=int, default=3072)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--skip-save", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this smoke test")

    from diffusers import QwenImageEditPlusPipeline

    print("Loading 4-bit Qwen pipeline...")
    print(f"  model_id={args.model_id}")
    pipe = QwenImageEditPlusPipeline.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
        cache_dir=args.cache_dir,
    )
    pipe.to("cuda")
    gpu_stats("after pipeline load")

    transformer = pipe.transformer
    transformer.train()
    transformer.requires_grad_(False)

    print("Preparing quantized transformer for k-bit LoRA training...")
    try:
        transformer = prepare_model_for_kbit_training(transformer, use_gradient_checkpointing=False)
    except Exception as exc:
        print(f"prepare_model_for_kbit_training warning: {exc}")

    target_modules = [m.strip() for m in args.target_modules.split(",") if m.strip()]
    print("Injecting LoRA...")
    print(f"  rank={args.rank} alpha={args.alpha}")
    print(f"  target_modules={target_modules}")

    lora_config = LoraConfig(
        r=args.rank,
        lora_alpha=args.alpha,
        init_lora_weights="gaussian",
        target_modules=target_modules,
        lora_dropout=0.0,
        bias="none",
    )
    transformer = get_peft_model(transformer, lora_config)
    pipe.transformer = transformer

    trainable, total = trainable_summary(transformer)
    print(f"Params: trainable={trainable:,} total={total:,} trainable_pct={100 * trainable / total:.6f}%")
    if trainable == 0:
        raise RuntimeError("No trainable LoRA parameters found")

    module_name, module = find_lora_wrapped_projection(transformer)
    print(f"Using module for synthetic backward: {module_name} ({module.__class__.__name__})")

    # Qwen transformer projection dimensions are 3072 -> 3072 for attention projections.
    # We directly call one real quantized+LoRA projection to validate gradient flow.
    device = next(module.parameters()).device
    x = torch.randn(2, args.seq_len, args.hidden_size, device=device, dtype=torch.bfloat16)

    # A tiny optimizer step catches more issues than backward alone.
    optimizer = torch.optim.AdamW([p for p in transformer.parameters() if p.requires_grad], lr=1e-4)
    optimizer.zero_grad(set_to_none=True)

    y = module(x)
    loss = (y.float() ** 2).mean()
    print(f"Synthetic loss: {loss.item():.8f}")
    loss.backward()

    nonzero_grad_tensors = 0
    grad_abs_sum = 0.0
    grad_examples = []
    for name, p in transformer.named_parameters():
        if p.requires_grad:
            if p.grad is not None:
                g = p.grad.detach().float().abs().sum().item()
                grad_abs_sum += g
                if g > 0:
                    nonzero_grad_tensors += 1
                    if len(grad_examples) < 8:
                        grad_examples.append((name, g))

    print(f"LoRA grad_abs_sum={grad_abs_sum:.8f}")
    print(f"LoRA nonzero_grad_tensors={nonzero_grad_tensors}")
    for name, g in grad_examples:
        print(f"  grad {name}: {g:.8f}")

    if grad_abs_sum <= 0 or nonzero_grad_tensors == 0:
        raise RuntimeError("LoRA gradients did not flow")

    optimizer.step()
    print("Optimizer step completed")

    if not args.skip_save:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        transformer.save_pretrained(output_dir)
        print(f"Saved LoRA adapter to {output_dir.resolve()}")

    del pipe, transformer, module, x, y, loss
    gc.collect()
    torch.cuda.empty_cache()
    gpu_stats("after cleanup")
    print("OK: quantized LoRA gradient smoke test passed")


if __name__ == "__main__":
    main()
