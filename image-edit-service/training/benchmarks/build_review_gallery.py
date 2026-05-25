#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any


def latest_run(repo_root: Path) -> Path:
    candidates = sorted((repo_root / "runs" / "benchmarks").glob("*_qwen_base_v1"))
    if not candidates:
        raise SystemExit("No benchmark runs found under runs/benchmarks")
    return candidates[-1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(from_dir: Path, to_path: Path) -> str:
    return to_path.resolve().relative_to(from_dir.resolve()) if False else Path(
        __import__("os").path.relpath(to_path.resolve(), from_dir.resolve())
    ).as_posix()


def collect_endpoint_items(run_dir: Path, endpoint: str) -> list[dict[str, Any]]:
    response_files = sorted((run_dir / endpoint).glob("**/*.response.json"))
    items: list[dict[str, Any]] = []
    for rf in response_files:
        obj = load_json(rf)
        row = obj.get("manifest_row", {})
        result = obj.get("result", {})
        rid = row.get("id") or rf.stem.replace(".response", "")
        output_path = rf.with_suffix("")  # remove .json -> .response, then below
        # actual output png lives as same stem without .response
        output_png = rf.with_name(rf.name.replace(".response.json", ".png"))
        items.append(
            {
                "id": rid,
                "endpoint": obj.get("endpoint", endpoint),
                "manifest_row": row,
                "result": result,
                "wall_time_ms": obj.get("wall_time_ms"),
                "output_png": output_png,
                "response_json": rf,
            }
        )
    return items


def img_tag(path: str, cls: str = "img") -> str:
    return f'<img class="{cls}" src="{path}" loading="lazy" />'


def build_card(item: dict[str, Any], review_dir: Path, repo_root: Path) -> str:
    row = item["manifest_row"]
    result = item["result"]
    endpoint = item["endpoint"]

    output_rel = rel(review_dir, item["output_png"])
    resp_rel = rel(review_dir, item["response_json"])

    inputs_html = []
    if endpoint == "ghost-mannequin":
        for key in ["image", "back_image"]:
            if row.get(key):
                p = (repo_root / row[key]).resolve()
                inputs_html.append(
                    f'<div><div class="lbl">{key}</div>{img_tag(rel(review_dir, p), "thumb")}</div>'
                )
    elif endpoint == "try-on":
        for key in ["avatar", "garment"]:
            if row.get(key):
                p = (repo_root / row[key]).resolve()
                inputs_html.append(
                    f'<div><div class="lbl">{key}</div>{img_tag(rel(review_dir, p), "thumb")}</div>'
                )
    elif endpoint == "edit":
        if row.get("image"):
            p = (repo_root / row["image"]).resolve()
            inputs_html.append(f'<div><div class="lbl">image</div>{img_tag(rel(review_dir, p), "thumb")}</div>')

    prompt = row.get("prompt") or row.get("custom_prompt") or ""
    success = bool(result.get("success", False))
    status_cls = "ok" if success else "err"

    return f"""
    <div class=\"card\">
      <div class=\"head\">
        <span class=\"id\">{row.get('id')}</span>
        <span class=\"status {status_cls}\">{'OK' if success else 'ERR'}</span>
        <span class=\"meta\">proc={result.get('processing_time_ms')}ms wall={item.get('wall_time_ms')}ms</span>
      </div>
      <div class=\"grid\">
        <div class=\"inputs\">{''.join(inputs_html)}</div>
        <div class=\"out\">
          <div class=\"lbl\">output</div>
          {img_tag(output_rel, 'outimg')}
          <div><a href=\"{output_rel}\" target=\"_blank\">open image</a> · <a href=\"{resp_rel}\" target=\"_blank\">response json</a></div>
        </div>
      </div>
      <div class=\"prompt\">{prompt}</div>
    </div>
    """


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--run-dir", default="", help="runs/benchmarks/<run>. If empty, latest *_qwen_base_v1")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    run_dir = (repo_root / args.run_dir).resolve() if args.run_dir else latest_run(repo_root)
    if not run_dir.exists():
        raise SystemExit(f"Run dir not found: {run_dir}")

    review_dir = run_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    sections = ["ghost", "look", "avatar"]
    section_html = []
    counts = {}

    for s in sections:
        items = collect_endpoint_items(run_dir, s)
        counts[s] = len(items)
        cards = "\n".join(build_card(it, review_dir, repo_root) for it in items)
        section_html.append(f"<h2>{s} ({len(items)})</h2>\n<div class='cards'>{cards}</div>")

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Wardrub Benchmark Review</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 16px; background:#fafafa; }}
    h1 {{ margin-bottom: 4px; }}
    .sub {{ color:#555; margin-bottom: 16px; }}
    .cards {{ display: grid; grid-template-columns: 1fr; gap: 14px; }}
    .card {{ background:white; border:1px solid #ddd; border-radius:10px; padding:10px; }}
    .head {{ display:flex; gap:10px; align-items:center; margin-bottom:8px; flex-wrap:wrap; }}
    .id {{ font-weight:700; }}
    .status {{ padding:2px 8px; border-radius:12px; font-size:12px; }}
    .status.ok {{ background:#d8f5df; color:#196b2e; }}
    .status.err {{ background:#ffdcdc; color:#7a1f1f; }}
    .meta {{ color:#555; font-size:12px; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:12px; }}
    .inputs {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .lbl {{ font-size:12px; color:#444; margin-bottom:4px; }}
    img.thumb {{ width:180px; height:auto; border:1px solid #ccc; border-radius:6px; }}
    img.outimg {{ width:320px; max-width:100%; height:auto; border:1px solid #ccc; border-radius:6px; }}
    .prompt {{ margin-top:8px; font-size:12px; color:#333; white-space:pre-wrap; }}
  </style>
</head>
<body>
  <h1>Wardrub Benchmark Review</h1>
  <div class=\"sub\">run: {run_dir.name} · counts: ghost={counts.get('ghost',0)}, look={counts.get('look',0)}, avatar={counts.get('avatar',0)}</div>
  {''.join(section_html)}
</body>
</html>
"""

    out = review_dir / "index.html"
    out.write_text(html, encoding="utf-8")

    (review_dir / "summary.json").write_text(json.dumps({"run": run_dir.name, "counts": counts}, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
