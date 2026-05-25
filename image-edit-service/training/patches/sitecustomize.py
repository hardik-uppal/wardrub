"""Wardrub runtime patches for training monitoring.

This file is loaded automatically by Python when its directory is on PYTHONPATH.
It intentionally does nothing unless WARDRUB_ENABLE_DIFFSYNTH_MONITORING=1.

The patch wraps DiffSynth's ModelLogger so we get:
- per-step loss lines in stdout/log files
- CSV loss log under WARDRUB_TRAINING_MONITOR_DIR
- optional TensorBoard scalars
- optional WandB scalars when WANDB_API_KEY is present
"""
from __future__ import annotations

import csv
import os
import time
from pathlib import Path


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


if _truthy(os.environ.get("WARDRUB_ENABLE_DIFFSYNTH_MONITORING")):
    try:
        import diffsynth.diffusion as _diffusion
        import diffsynth.diffusion.logger as _logger

        _BaseModelLogger = _logger.ModelLogger

        class WardrubModelLogger(_BaseModelLogger):  # type: ignore[misc]
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                run_id = os.environ.get("WARDRUB_RUN_ID") or os.environ.get("WANDB_RUN_ID") or time.strftime("%Y%m%d_%H%M%S")
                monitor_dir = os.environ.get("WARDRUB_TRAINING_MONITOR_DIR")
                if not monitor_dir:
                    monitor_dir = os.path.join(self.output_path, "monitor", run_id)
                self.wardrub_run_id = run_id
                self.wardrub_monitor_dir = Path(monitor_dir)
                self._wardrub_initialized = False
                self._wardrub_csv_file = None
                self._wardrub_csv_writer = None
                self._wardrub_tb_writer = None
                self._wardrub_wandb = None
                self._wardrub_start_time = time.time()

            def _wardrub_init_once(self, accelerator):
                if self._wardrub_initialized:
                    return
                self._wardrub_initialized = True
                if not getattr(accelerator, "is_main_process", True):
                    return

                self.wardrub_monitor_dir.mkdir(parents=True, exist_ok=True)
                csv_path = self.wardrub_monitor_dir / "loss.csv"
                is_new = not csv_path.exists() or csv_path.stat().st_size == 0
                self._wardrub_csv_file = csv_path.open("a", newline="", encoding="utf-8")
                self._wardrub_csv_writer = csv.DictWriter(
                    self._wardrub_csv_file,
                    fieldnames=["wall_time", "elapsed_sec", "step", "loss"],
                )
                if is_new:
                    self._wardrub_csv_writer.writeheader()
                    self._wardrub_csv_file.flush()

                if _truthy(os.environ.get("WARDRUB_ENABLE_TENSORBOARD", "1")):
                    try:
                        from torch.utils.tensorboard import SummaryWriter
                        self._wardrub_tb_writer = SummaryWriter(log_dir=str(self.wardrub_monitor_dir / "tensorboard"))
                    except Exception as exc:  # pragma: no cover - best effort only
                        print(f"WARDRUB_MONITOR tensorboard_unavailable={exc!r}", flush=True)

                wandb_enabled = _truthy(os.environ.get("WARDRUB_ENABLE_WANDB")) or (
                    os.environ.get("WARDRUB_ENABLE_WANDB", "auto").lower() == "auto"
                    and bool(os.environ.get("WANDB_API_KEY"))
                )
                if wandb_enabled:
                    try:
                        import wandb

                        safe_config_keys = [
                            "DATASET_BASE_PATH",
                            "METADATA_PATH",
                            "OUTPUT_PATH",
                            "DATASET_REPEAT",
                            "NUM_EPOCHS",
                            "LEARNING_RATE",
                            "LORA_RANK",
                            "MAX_PIXELS",
                            "DATASET_NUM_WORKERS",
                            "LORA_TARGET_MODULES",
                        ]
                        safe_config = {k: os.environ.get(k) for k in safe_config_keys if os.environ.get(k) is not None}
                        self._wardrub_wandb = wandb
                        wandb.init(
                            project=os.environ.get("WANDB_PROJECT", "wardrub-vton-lora"),
                            entity=os.environ.get("WANDB_ENTITY") or None,
                            name=os.environ.get("WANDB_RUN_NAME") or self.wardrub_run_id,
                            group=os.environ.get("WANDB_RUN_GROUP") or "runpod-smoke",
                            id=os.environ.get("WANDB_RUN_ID") or self.wardrub_run_id,
                            resume=os.environ.get("WANDB_RESUME", "allow"),
                            dir=str(self.wardrub_monitor_dir),
                            config=safe_config,
                        )
                    except Exception as exc:  # pragma: no cover - best effort only
                        print(f"WARDRUB_MONITOR wandb_unavailable={exc!r}", flush=True)

                print(f"WARDRUB_MONITOR dir={self.wardrub_monitor_dir}", flush=True)

            @staticmethod
            def _loss_to_float(loss):
                try:
                    if hasattr(loss, "detach"):
                        loss = loss.detach()
                    if hasattr(loss, "float"):
                        loss = loss.float()
                    if hasattr(loss, "mean"):
                        loss = loss.mean()
                    if hasattr(loss, "item"):
                        return float(loss.item())
                    return float(loss)
                except Exception:
                    return None

            def on_step_end(self, accelerator, model, save_steps=None, **kwargs):
                super().on_step_end(accelerator, model, save_steps=save_steps, **kwargs)
                self._wardrub_init_once(accelerator)
                if not getattr(accelerator, "is_main_process", True):
                    return

                loss_value = self._loss_to_float(kwargs.get("loss"))
                if loss_value is None:
                    return

                now = time.time()
                elapsed = now - self._wardrub_start_time
                row = {
                    "wall_time": int(now),
                    "elapsed_sec": round(elapsed, 3),
                    "step": int(self.num_steps),
                    "loss": loss_value,
                }

                if self._wardrub_csv_writer is not None:
                    self._wardrub_csv_writer.writerow(row)
                    self._wardrub_csv_file.flush()

                if self._wardrub_tb_writer is not None:
                    self._wardrub_tb_writer.add_scalar("train/loss", loss_value, self.num_steps)
                    self._wardrub_tb_writer.flush()

                if self._wardrub_wandb is not None:
                    self._wardrub_wandb.log({"train/loss": loss_value, "elapsed_sec": elapsed}, step=self.num_steps)

                print(
                    f"WARDRUB_TRAINING_METRIC step={self.num_steps} loss={loss_value:.8f} elapsed_sec={elapsed:.1f}",
                    flush=True,
                )

            def on_training_end(self, accelerator, model, save_steps=None):
                try:
                    super().on_training_end(accelerator, model, save_steps=save_steps)
                finally:
                    if getattr(accelerator, "is_main_process", True):
                        if self._wardrub_tb_writer is not None:
                            self._wardrub_tb_writer.close()
                        if self._wardrub_csv_file is not None:
                            self._wardrub_csv_file.close()
                        if self._wardrub_wandb is not None:
                            self._wardrub_wandb.finish()

        _logger.ModelLogger = WardrubModelLogger
        _diffusion.ModelLogger = WardrubModelLogger
        print("WARDRUB_MONITOR DiffSynth ModelLogger patched", flush=True)
    except Exception as exc:  # pragma: no cover - patch must never break training startup
        print(f"WARDRUB_MONITOR patch_failed={exc!r}", flush=True)
