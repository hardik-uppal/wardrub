#!/usr/bin/env python3
"""Persistent progress tracker for long-running ML tasks.

Writes a JSON progress file that can be read at any time.
Usage:
  from progress_tracker import ProgressTracker
  tracker = ProgressTracker("runs/progress/benchmark_avatar.json", total=24)
  for i, result in enumerate(run_benchmark()):
      tracker.update(i+1, detail=result["sample_id"])
  tracker.finish()
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Any


class ProgressTracker:
    def __init__(self, path: str | Path, total: int, task: str = "", metadata: dict | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.total = total
        self.task = task
        self.start_time = time.time()
        self.state = {
            "task": task,
            "total": total,
            "completed": 0,
            "failed": 0,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "elapsed_seconds": 0,
            "eta_seconds": None,
            "rate_per_minute": None,
            "status": "running",
            "last_detail": "",
            "errors": [],
            "metadata": metadata or {},
        }
        self._save()

    def update(self, completed: int, failed: int = 0, detail: str = "", metadata: dict | None = None):
        elapsed = time.time() - self.start_time
        self.state["completed"] = completed
        self.state["failed"] = failed if failed else self.state["failed"]
        self.state["elapsed_seconds"] = round(elapsed, 1)
        self.state["updated_at"] = datetime.now().isoformat()
        self.state["last_detail"] = detail

        if completed > 0:
            rate = completed / (elapsed / 60) if elapsed > 0 else 0
            self.state["rate_per_minute"] = round(rate, 2)
            remaining = self.total - completed
            self.state["eta_seconds"] = round(remaining / (rate / 60)) if rate > 0 else None

        if metadata:
            self.state["metadata"].update(metadata)

        self._save()

    def add_error(self, error: str):
        self.state["errors"].append({"time": datetime.now().isoformat(), "error": str(error)[:500]})
        self._save()

    def finish(self, status: str = "done"):
        elapsed = time.time() - self.start_time
        self.state["status"] = status
        self.state["elapsed_seconds"] = round(elapsed, 1)
        self.state["updated_at"] = datetime.now().isoformat()
        self.state["eta_seconds"] = 0
        self._save()

    def fail(self, error: str):
        self.state["status"] = "failed"
        self.state["updated_at"] = datetime.now().isoformat()
        self.add_error(error)
        self._save()

    def _save(self):
        self.path.write_text(json.dumps(self.state, indent=2))

    def summary(self) -> str:
        s = self.state
        pct = (s["completed"] / s["total"] * 100) if s["total"] > 0 else 0
        elapsed = s["elapsed_seconds"]
        eta = s.get("eta_seconds")
        rate = s.get("rate_per_minute", 0)

        bar_width = 30
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        lines = [
            f"{'='*50}",
            f"Task: {s['task']}",
            f"Progress: {bar} {pct:.0f}%",
            f"Done: {s['completed']}/{s['total']} | Failed: {s['failed']} | Elapsed: {self._fmt_time(elapsed)}",
        ]
        if rate > 0:
            lines.append(f"Rate: {rate:.1f}/min | ETA: {self._fmt_time(eta) if eta else '...'}")
        if s["last_detail"]:
            lines.append(f"Last: {s['last_detail']}")
        lines.append(f"{'='*50}")
        return "\n".join(lines)

    @staticmethod
    def _fmt_time(seconds: float | None) -> str:
        if seconds is None:
            return "?"
        if seconds < 60:
            return f"{seconds:.0f}s"
        if seconds < 3600:
            return f"{seconds/60:.1f}m"
        return f"{seconds/3600:.1f}h"


def load_progress(path: str | Path) -> dict | None:
    """Read a progress file, returns None if not found."""
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return None
