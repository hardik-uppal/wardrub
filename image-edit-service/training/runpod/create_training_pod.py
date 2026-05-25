#!/usr/bin/env python3
"""Create a RunPod pod for Wardrub Qwen/DiffSynth LoRA training.

Secrets are read from environment and never printed.
Required: RUNPOD_API_KEY
Optional: HF_TOKEN/HUGGING_FACE_HUB_TOKEN/HUGGINGFACE_HUB_TOKEN, WANDB_API_KEY
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.runpod.io/graphql"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def gql(query: str, variables: dict | None = None) -> dict:
    key = os.environ.get("RUNPOD_API_KEY")
    if not key:
        raise SystemExit("RUNPOD_API_KEY is not set")
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"RunPod HTTP {exc.code}: {body[:2000]}") from exc


def env_list(args: argparse.Namespace) -> list[dict[str, str]]:
    hf = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    env = [
        {"key": "HF_HOME", "value": "/workspace/.cache/huggingface"},
        {"key": "HF_HUB_CACHE", "value": "/workspace/.cache/huggingface/hub"},
        {"key": "HF_HUB_ENABLE_HF_TRANSFER", "value": "1"},
        {"key": "MODELSCOPE_CACHE", "value": "/workspace/.cache/modelscope"},
        {"key": "TOKENIZERS_PARALLELISM", "value": "false"},
        {"key": "WANDB_PROJECT", "value": args.wandb_project},
        {"key": "WANDB_RUN_GROUP", "value": args.wandb_group},
    ]
    if hf:
        env.extend([
            {"key": "HF_TOKEN", "value": hf},
            {"key": "HUGGING_FACE_HUB_TOKEN", "value": hf},
            {"key": "HUGGINGFACE_HUB_TOKEN", "value": hf},
        ])
    if os.environ.get("WANDB_API_KEY"):
        env.append({"key": "WANDB_API_KEY", "value": os.environ["WANDB_API_KEY"]})
    return env


def list_pods() -> None:
    data = gql("query { myself { pods { id name desiredStatus machineId gpuCount imageName costPerHr } } }")
    pods = data.get("data", {}).get("myself", {}).get("pods", [])
    print(json.dumps({"pods": pods}, indent=2))


def create(args: argparse.Namespace) -> int:
    mutation = """mutation Deploy($input: PodFindAndDeployOnDemandInput) {
      podFindAndDeployOnDemand(input: $input) {
        id name machineId desiredStatus imageName gpuCount podType costPerHr
      }
    }"""
    input_obj = {
        "name": args.name,
        "imageName": args.image,
        "gpuTypeId": args.gpu,
        "gpuCount": args.gpu_count,
        "cloudType": args.cloud,
        "containerDiskInGb": args.container_disk_gb,
        "volumeInGb": args.volume_gb,
        "volumeMountPath": args.volume_mount,
        "ports": args.ports,
        "env": env_list(args),
    }
    if args.dry_run:
        redacted = dict(input_obj)
        redacted["env"] = [{"key": item["key"], "value": "***" if "TOKEN" in item["key"] or item["key"] == "WANDB_API_KEY" else item["value"]} for item in input_obj["env"]]
        print(json.dumps(redacted, indent=2))
        return 0

    print(f"Creating pod name={args.name} gpu={args.gpu} cloud={args.cloud} volume={args.volume_gb}GB image={args.image}")
    data = gql(mutation, {"input": input_obj})
    pod = data.get("data", {}).get("podFindAndDeployOnDemand")
    if pod:
        print("CREATED")
        print(json.dumps(pod, indent=2))
        return 0
    print(json.dumps(data, indent=2))
    return 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="wardrub-qwen-lora-smoke")
    parser.add_argument("--gpu", default="NVIDIA A100 80GB PCIe")
    parser.add_argument("--gpu-count", type=int, default=1)
    parser.add_argument("--cloud", choices=["SECURE", "COMMUNITY"], default="SECURE")
    parser.add_argument("--image", default="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04")
    parser.add_argument("--container-disk-gb", type=int, default=80)
    parser.add_argument("--volume-gb", type=int, default=300)
    parser.add_argument("--volume-mount", default="/workspace")
    parser.add_argument("--ports", default="22/tcp,8888/http,6006/http")
    parser.add_argument("--wandb-project", default="wardrub-vton-lora")
    parser.add_argument("--wandb-group", default="runpod-smoke")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-pods", action="store_true")
    args = parser.parse_args()

    if args.list_pods:
        list_pods()
        return
    raise SystemExit(create(args))


if __name__ == "__main__":
    main()
