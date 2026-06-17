#!/usr/bin/env python3
"""Objective identity-preservation eval using InsightFace buffalo_l embeddings.

For avatar/edit benchmarks: compares the face embedding of the output image
against the face embedding of the input image. Reports cosine similarity.

Usage:
  python training/eval/score_identity_insightface.py \
    --manifest training/benchmarks/avatar_identity_lfw_small_v1_strict_s32.jsonl \
    --run-dir runs/benchmarks/20260524_054622_avatar_identity_nolightning_strict_s32 \
    --out runs/eval/insightface_scores.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_model() -> FaceAnalysis:
    app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


def get_face_embedding(app: FaceAnalysis, img_path: Path) -> np.ndarray | None:
    """Extract face embedding from image. Returns None if no face detected."""
    if not img_path.exists():
        return None
    img = cv2.imread(str(img_path))
    if img is None:
        return None
    # Resize tiny images so the detector can find faces (min 320px on shortest side)
    h, w = img.shape[:2]
    min_side = 320
    if h < min_side or w < min_side:
        scale = min_side / min(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    faces = app.get(img)
    if not faces:
        return None
    # Use the largest face
    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return largest.normed_embedding


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    parser = argparse.ArgumentParser(description="InsightFace identity eval")
    parser.add_argument("--manifest", required=True, help="Benchmark manifest JSONL")
    parser.add_argument("--run-dir", required=True, help="Benchmark run directory with eval/edit/*.png")
    parser.add_argument("--out", default=None, help="Output JSON path")
    parser.add_argument("--dataset-root", default=str(REPO_ROOT), help="Root for manifest paths")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    run_dir = Path(args.run_dir)
    dataset_root = Path(args.dataset_root)

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    # Load manifest
    samples = []
    with open(manifest_path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))

    print(f"Loading InsightFace buffalo_l...")
    app = load_model()
    print(f"Loaded. Evaluating {len(samples)} samples against {run_dir.name}")

    results = []
    identity_groups = {}  # identity -> list of similarities

    for sample in samples:
        sample_id = sample["id"]
        identity = sample.get("tags", {}).get("identity", "unknown")
        input_path = dataset_root / sample["image"]
        output_path = run_dir / "eval" / "edit" / f"{sample_id}.png"

        input_emb = get_face_embedding(app, input_path)
        output_emb = get_face_embedding(app, output_path)

        result = {
            "sample_id": sample_id,
            "identity": identity,
            "input_image": str(sample["image"]),
            "output_image": str(output_path) if output_path.exists() else None,
            "input_face_detected": input_emb is not None,
            "output_face_detected": output_emb is not None,
        }

        if input_emb is not None and output_emb is not None:
            sim = cosine_similarity(input_emb, output_emb)
            result["identity_similarity"] = round(sim, 4)
            identity_groups.setdefault(identity, []).append(sim)
        else:
            result["identity_similarity"] = None
            if input_emb is None:
                result["error"] = "No face in input image"
            else:
                result["error"] = "No face in output image"

        results.append(result)

    # Summary
    all_sims = [r["identity_similarity"] for r in results if r["identity_similarity"] is not None]
    summary = {
        "total_samples": len(results),
        "face_detected_both": len(all_sims),
        "face_missing_input": sum(1 for r in results if not r.get("input_face_detected")),
        "face_missing_output": sum(1 for r in results if not r.get("output_face_detected")),
    }
    if all_sims:
        summary["identity_similarity"] = {
            "mean": round(float(np.mean(all_sims)), 4),
            "median": round(float(np.median(all_sims)), 4),
            "std": round(float(np.std(all_sims)), 4),
            "min": round(float(np.min(all_sims)), 4),
            "max": round(float(np.max(all_sims)), 4),
        }
        # Per-identity breakdown
        per_identity = {}
        for ident, sims in sorted(identity_groups.items()):
            per_identity[ident] = {
                "count": len(sims),
                "mean_similarity": round(float(np.mean(sims)), 4),
                "std": round(float(np.std(sims)), 4),
            }
        summary["per_identity"] = per_identity

    output = {
        "eval_method": "insightface_buffalo_l_cosine",
        "manifest": str(manifest_path),
        "run_dir": str(run_dir),
        "summary": summary,
        "results": results,
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2))
        print(f"\nSaved: {out_path}")
    else:
        print(json.dumps(output, indent=2))

    # Print summary
    print(f"\n{'='*50}")
    print(f"InsightFace Identity Eval — {run_dir.name}")
    print(f"{'='*50}")
    print(f"Total samples: {summary['total_samples']}")
    print(f"Both faces detected: {summary['face_detected_both']}")
    if all_sims:
        print(f"Mean identity sim: {summary['identity_similarity']['mean']:.4f}")
        print(f"Median: {summary['identity_similarity']['median']:.4f}")
        print(f"Range: [{summary['identity_similarity']['min']:.4f}, {summary['identity_similarity']['max']:.4f}]")
        print(f"\nPer identity:")
        for ident, info in summary.get("per_identity", {}).items():
            print(f"  {ident:25s}: {info['mean_similarity']:.4f} ± {info['std']:.4f} (n={info['count']})")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
