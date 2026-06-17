#!/usr/bin/env python3
"""Run benchmarks with persistent progress tracking.

Usage:
  python training/eval/run_benchmark_with_progress.py \
    --manifest training/benchmarks/avatar_identity_lfw_small_v1_strict_s32.jsonl \
    --endpoint edit \
    --limit 24 \
    --out runs/benchmarks/my_run \
    --progress runs/progress/my_run.json
"""
from __future__ import annotations

import argparse, base64, json, sys, time, traceback
from pathlib import Path
from typing import Any

import httpx

# Add parent to path for progress_tracker import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from progress_tracker import ProgressTracker

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--endpoint", required=True, choices=["edit", "ghost-mannequin", "try-on"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--out", required=True)
    parser.add_argument("--progress", default=None)
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--dataset-root", default=str(REPO_ROOT))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    # Load manifest
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    samples = []
    with open(manifest_path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    if args.limit > 0:
        samples = samples[:args.limit]

    total = len(samples)
    print(f"Running {total} samples from {manifest_path.name}")

    # Progress tracker
    progress_path = Path(args.progress) if args.progress else Path(args.out) / "progress.json"
    tracker = ProgressTracker(
        progress_path,
        total=total,
        task=f"{manifest_path.name} ({args.endpoint})",
        metadata={"endpoint": args.endpoint, "base_url": args.base_url}
    )

    # Output dir
    out_dir = Path(args.out)
    eval_dir = out_dir / "eval" / args.endpoint
    eval_dir.mkdir(parents=True, exist_ok=True)

    client = httpx.Client(timeout=args.timeout)
    success = 0
    failed = 0

    for i, sample in enumerate(samples):
        sample_id = sample["id"]
        seed = sample.get("seed", args.seed_start + i)
        print(f"[{i+1}/{total}] {sample_id}...", end=" ", flush=True)

        try:
            if args.endpoint == "edit":
                img_path = (Path(args.dataset_root) / sample["image"]).resolve()
                if not img_path.exists():
                    raise FileNotFoundError(f"Image not found: {img_path}")
                
                with open(img_path, "rb") as f:
                    img_bytes = f.read()

                prompt = sample.get("prompt", "Create a clean neutral portrait of THE SAME PERSON from the input photo. Preserve exact identity, face, skin tone, hair. Neutral white/light-gray background. Natural studio lighting. Head-and-shoulders portrait composition.")
                
                r = client.post(
                    f"{args.base_url}/edit",
                    files={"image": (img_path.name, img_bytes, "image/jpeg")},
                    data={"prompt": prompt, "steps": str(sample.get("steps", 28)), "seed": str(seed)},
                )
                r.raise_for_status()
                result = r.json()
                
                img_data = base64.b64decode(result["image_base64"])
                out_path = eval_dir / f"{sample_id}.png"
                out_path.write_bytes(img_data)
                
                # Save response metadata
                resp_path = eval_dir / f"{sample_id}.response.json"
                resp_path.write_text(json.dumps({
                    "sample_id": sample_id,
                    "seed": seed,
                    "processing_time_ms": result.get("processing_time_ms"),
                    "input_size": f"{img_path.stat().st_size}B",
                    "output_size": f"{len(img_data)}B",
                }, indent=2))

                elapsed = result.get("processing_time_ms", 0) / 1000
                print(f"✅ {elapsed:.1f}s")
                success += 1

            elif args.endpoint == "ghost-mannequin":
                img_path = (Path(args.dataset_root) / sample["image"]).resolve()
                if not img_path.exists():
                    raise FileNotFoundError(f"Image not found: {img_path}")
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                data = {"category": sample.get("category", "top"), "seed": str(seed)}
                if sample.get("custom_prompt"):
                    data["custom_prompt"] = sample["custom_prompt"]
                r = client.post(
                    f"{args.base_url}/ghost-mannequin",
                    files={"image": (img_path.name, img_bytes, "image/jpeg")},
                    data=data,
                )
                r.raise_for_status()
                result = r.json()
                img_data = base64.b64decode(result["image_base64"])
                (eval_dir / f"{sample_id}.png").write_bytes(img_data)
                elapsed = result.get("processing_time_ms", 0) / 1000
                print(f"✅ {elapsed:.1f}s")
                success += 1

            elif args.endpoint == "try-on":
                avatar_path = (Path(args.dataset_root) / sample["avatar"]).resolve()
                garment_path = (Path(args.dataset_root) / sample["garment"]).resolve()
                if not avatar_path.exists():
                    raise FileNotFoundError(f"Avatar not found: {avatar_path}")
                if not garment_path.exists():
                    raise FileNotFoundError(f"Garment not found: {garment_path}")
                with open(avatar_path, "rb") as f:
                    avatar_bytes = f.read()
                with open(garment_path, "rb") as f:
                    garment_bytes = f.read()
                r = client.post(
                    f"{args.base_url}/try-on",
                    files={
                        "avatar": (avatar_path.name, avatar_bytes, "image/jpeg"),
                        "garment": (garment_path.name, garment_bytes, "image/jpeg"),
                    },
                    data={"category": sample.get("category", "top"), "seed": str(seed)},
                )
                r.raise_for_status()
                result = r.json()
                img_data = base64.b64decode(result["image_base64"])
                (eval_dir / f"{sample_id}.png").write_bytes(img_data)
                elapsed = result.get("processing_time_ms", 0) / 1000
                print(f"✅ {elapsed:.1f}s")
                success += 1

        except Exception as e:
            print(f"❌ {str(e)[:100]}")
            tracker.add_error(f"{sample_id}: {str(e)[:300]}")
            failed += 1

        tracker.update(success + failed, failed=failed, detail=f"{sample_id} ({success} ok, {failed} fail)")
        
        # Print summary every 5 samples
        if (i + 1) % 5 == 0:
            print(tracker.summary())

    tracker.finish("done" if failed == 0 else "partial")
    print(f"\n{tracker.summary()}")
    print(f"Output: {eval_dir}")


if __name__ == "__main__":
    main()
