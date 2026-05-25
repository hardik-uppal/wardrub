#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path


COLUMNS = [
    "timestamp",
    "experiment_id",
    "task",
    "phase",
    "dataset_chunk",
    "model_config",
    "prompt_profile",
    "steps",
    "manifest",
    "params_json",
    "run_dir",
    "count",
    "success_count",
    "notes",
]


def slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "na"


def make_experiment_id(task: str, dataset_chunk: str, model_config: str, prompt_profile: str, phase: str, steps: int | None) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    parts = [
        "exp",
        stamp,
        slug(task),
        slug(dataset_chunk or "chunk-na"),
        slug(model_config),
        slug(prompt_profile or "prompt-default"),
        f"s{steps}" if steps is not None else "sna",
        slug(phase),
    ]
    return "__".join(parts)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default="training/experiments/registry.csv")
    p.add_argument("--experiment-id", default="")
    p.add_argument("--task", required=True)
    p.add_argument("--phase", default="eval")
    p.add_argument("--dataset-chunk", default="")
    p.add_argument("--model-config", required=True)
    p.add_argument("--prompt-profile", default="")
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--manifest", required=True)
    p.add_argument("--params-json", default="{}")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--count", type=int, default=0)
    p.add_argument("--success-count", type=int, default=0)
    p.add_argument("--notes", default="")
    return p.parse_args()


def read_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def ensure_registry_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()
        return

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()
        return

    old_header = rows[0]
    if old_header == COLUMNS:
        return

    # Migrate old schema to new schema.
    existing = read_existing_rows(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for r in existing:
            writer.writerow(
                {
                    "timestamp": r.get("timestamp", ""),
                    "experiment_id": r.get("experiment_id", ""),
                    "task": r.get("task", ""),
                    "phase": r.get("phase", ""),
                    "dataset_chunk": r.get("dataset_chunk", ""),
                    "model_config": r.get("model_config", ""),
                    "prompt_profile": r.get("prompt_profile", ""),
                    "steps": r.get("steps", ""),
                    "manifest": r.get("manifest", ""),
                    "params_json": r.get("params_json", ""),
                    "run_dir": r.get("run_dir", ""),
                    "count": r.get("count", "0"),
                    "success_count": r.get("success_count", "0"),
                    "notes": r.get("notes", ""),
                }
            )


def main() -> None:
    args = parse_args()
    reg = Path(args.registry)

    ensure_registry_schema(reg)

    # Validate JSON early
    json.loads(args.params_json)

    exp_id = args.experiment_id.strip() or make_experiment_id(
        task=args.task,
        dataset_chunk=args.dataset_chunk,
        model_config=args.model_config,
        prompt_profile=args.prompt_profile,
        phase=args.phase,
        steps=args.steps,
    )

    row = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "experiment_id": exp_id,
        "task": args.task,
        "phase": args.phase,
        "dataset_chunk": args.dataset_chunk,
        "model_config": args.model_config,
        "prompt_profile": args.prompt_profile,
        "steps": "" if args.steps is None else str(args.steps),
        "manifest": args.manifest,
        "params_json": args.params_json,
        "run_dir": args.run_dir,
        "count": str(args.count),
        "success_count": str(args.success_count),
        "notes": args.notes,
    }

    with reg.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=COLUMNS).writerow(row)

    print("logged", exp_id)


if __name__ == "__main__":
    main()
