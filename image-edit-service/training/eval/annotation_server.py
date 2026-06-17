#!/usr/bin/env python3
"""Serve the Wardrub benchmark annotation page + images over HTTP.

Usage:
  cd /home/hardik/Projects/wardrub/image-edit-service
  source venv/bin/activate
  python training/eval/annotation_server.py

Then open http://localhost:8090 in your browser.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BENCHMARKS_DIR = REPO_ROOT / "training" / "benchmarks"
RUNS_DIR = REPO_ROOT / "runs" / "benchmarks"


def build_manifest_index() -> list[dict]:
    """Collect all benchmark runs with metadata for the annotation page."""
    entries = []

    # Scan benchmark manifests
    for mf_path in sorted(BENCHMARKS_DIR.glob("*.jsonl")):
        manifest = {"name": mf_path.name, "path": str(mf_path.relative_to(REPO_ROOT)), "samples": []}
        with open(mf_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                sample = json.loads(line)
                manifest["samples"].append(sample)
        entries.append(manifest)

    # Scan runs
    runs = []
    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        run_info = {}
        info_file = run_dir / "_run_info.txt"
        if info_file.exists():
            for line in info_file.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    run_info[k.strip()] = v.strip()

        summary_file = run_dir / "eval" / "summary.json"
        summary = None
        if summary_file.exists():
            summary = json.loads(summary_file.read_text())

        gen_dir = run_dir / "eval" / "edit"
        generated = {}
        if gen_dir.is_dir():
            for img in sorted(gen_dir.iterdir()):
                if img.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    sample_id = img.stem  # e.g., "id_Ariel_Sharon_0001"
                    generated[sample_id] = str(img.relative_to(REPO_ROOT))

        runs.append({
            "name": run_dir.name,
            "info": run_info,
            "summary": summary,
            "generated": generated,
            "count": len(generated),
        })

    return {
        "manifests": [m for m in entries if m["samples"]],
        "runs": runs,
    }


class AnnotationHandler(http.server.SimpleHTTPRequestHandler):
    index_data: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/index":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(self.index_data, indent=2).encode())
            return

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = Path(__file__).parent / "annotation.html"
            self.wfile.write(html_path.read_bytes())
            return

        # Serve annotation.html directly too
        if parsed.path == "/annotation.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = Path(__file__).parent / "annotation.html"
            self.wfile.write(html_path.read_bytes())
            return

        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Quieter logging
        if "/api/" in str(args[0]) or ".png" in str(args[0]) or ".jpg" in str(args[0]):
            return
        super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="Wardrub annotation server")
    parser.add_argument("--port", type=int, default=8090, help="Port to serve on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    # Build index
    index = build_manifest_index()
    AnnotationHandler.index_data = index

    print(f"\n  Wardrub Annotation Server")
    print(f"  Serving from: {REPO_ROOT}")
    print(f"  URL: http://localhost:{args.port}\n")
    print(f"  {len(index['manifests'])} manifest(s), {len(index['runs'])} benchmark run(s)\n")

    server = http.server.HTTPServer((args.host, args.port), AnnotationHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
