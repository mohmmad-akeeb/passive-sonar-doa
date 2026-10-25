"""Train a classifier and write checkpoints plus JSON metrics."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import time

import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from tqdm import tqdm

from sonar_sim.models import SoftCrossEntropyLoss, build_model
from sonar_sim.training.config import TrainConfig

logger = logging.getLogger(__name__)


def create_results_dir(root: Path, model_name: str) -> dict[str, Path]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_root = Path(root) / model_name / stamp
    paths = {"root": run_root, "models": run_root / "models", "json": run_root / "json"}
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _json_dump(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _measure_model_complexity(
    model: torch.nn.Module,
    sample_input: torch.Tensor,
    model_path: Path,
    device: torch.device,
) -> dict:
    """Return FLOPs, parameter counts, inference time (ms), and file size (MB)."""
    complexity: dict = {}

    # --- parameter counts (no external dep required) ---
    total_params = sum(p.numel() for p in model.parameters())
    learnable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    complexity["total_parameters"] = int(total_params)
    complexity["learnable_parameters"] = int(learnable_params)

    # --- FLOPs via thop (optional dep — skip gracefully if absent) ---
    try:
        from thop import profile as thop_profile  # type: ignore
        flops, _ = thop_profile(model, inputs=(sample_input,), verbose=False)
        complexity["flops"] = float(flops)
    except Exception:
        complexity["flops"] = None

    # --- inference latency ---
    model.eval()
    with torch.no_grad():
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            starter = torch.cuda.Event(enable_timing=True)
            ender = torch.cuda.Event(enable_timing=True)
            starter.record()
            _ = model(sample_input)
            ender.record()
            torch.cuda.synchronize()
            complexity["inference_time_ms"] = float(starter.elapsed_time(ender))
        else:
            t0 = time.perf_counter()
            _ = model(sample_input)
            complexity["inference_time_ms"] = (time.perf_counter() - t0) * 1000.0

    # --- file size ---
    if model_path.exists():
        complexity["model_size_mb"] = model_path.stat().st_size / (1024 * 1024)
    else:
        complexity["model_size_mb"] = None

    return complexity


def train_and_evaluate(
    config: TrainConfig,
    train_loader,
    val_loader,
    test_loader,
    device: torch.device,
    result_paths: dict[str, Path],
) -> dict:
    model = build_model(
        config.model_name,
        num_sensors=config.num_sensors,
        num_classes=config.num_classes,
        **config.model_kwargs,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.learning_rate, weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=config.scheduler_factor,
        patience=config.scheduler_patience,
    )
    criterion = SoftCrossEntropyLoss()

    best_val_loss = float("inf")
    best_epoch = -1
    best_state = None
    patience_counter = 0

    # Training history — epoch-indexed lists for easy JSON consumption by plots
    history: dict[str, list] = {
        "epoch": [],
        "train_loss": [],
        "val_loss": [],
        "train_acc": [],
        "val_acc": [],
    }

    # ── training loop ──────────────────────────────────────────────────────────
    for epoch in range(config.epochs):
        t0 = time.perf_counter()
        model.train()
        train_loss = train_correct = train_total = 0

        for batch_x, batch_y in tqdm(train_loader, desc=f"Train {epoch + 1}", leave=False):
            batch_x = batch_x.to(device, non_blocking=True)
            batch_y = batch_y.to(device, non_blocking=True)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * batch_x.size(0)
            train_correct += (logits.argmax(1) == batch_y.argmax(1)).sum().item()
            train_total += batch_x.size(0)

        model.eval()
        val_loss = val_correct = val_total = 0
        with torch.no_grad():
            for batch_x, batch_y in tqdm(val_loader, desc=f"Val {epoch + 1}", leave=False):
                batch_x = batch_x.to(device, non_blocking=True)
                batch_y = batch_y.to(device, non_blocking=True)
                logits = model(batch_x)
                loss = criterion(logits, batch_y)
                val_loss += loss.item() * batch_x.size(0)
                val_correct += (logits.argmax(1) == batch_y.argmax(1)).sum().item()
                val_total += batch_x.size(0)

        tr_loss = train_loss / max(train_total, 1)
        vl_loss = val_loss / max(val_total, 1)
        tr_acc = train_correct / max(train_total, 1)
        vl_acc = val_correct / max(val_total, 1)

        history["epoch"].append(epoch + 1)
        history["train_loss"].append(float(tr_loss))
        history["val_loss"].append(float(vl_loss))
        history["train_acc"].append(float(tr_acc))
        history["val_acc"].append(float(vl_acc))

        scheduler.step(vl_loss)
        logger.info(
            "Epoch %03d | train %.4f | val %.4f | val_acc %.4f | %.1fs",
            epoch + 1, tr_loss, vl_loss, vl_acc, time.perf_counter() - t0,
        )

        if vl_loss < best_val_loss:
            best_val_loss = vl_loss
            best_epoch = epoch + 1
            best_state = deepcopy(model.state_dict())
            torch.save(best_state, result_paths["models"] / "best_model.pth")
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                logger.info("Early stopping at epoch %d.", epoch + 1)
                break

    if best_state is None:
        best_state = model.state_dict()
        torch.save(best_state, result_paths["models"] / "best_model.pth")
    model.load_state_dict(best_state)
    model.eval()

    # ── test set evaluation ────────────────────────────────────────────────────
    preds: list[int] = []
    targets: list[int] = []
    with torch.no_grad():
        for batch_x, batch_y in tqdm(test_loader, desc="Test"):
            logits = model(batch_x.to(device, non_blocking=True))
            preds.extend(logits.argmax(1).cpu().tolist())
            targets.extend(batch_y.argmax(1).cpu().tolist())

    metrics = {
        "model_name": config.model_name,
        "accuracy": float(accuracy_score(targets, preds)),
        "precision": float(precision_score(targets, preds, average="weighted", zero_division=0)),
        "recall": float(recall_score(targets, preds, average="weighted", zero_division=0)),
        "f1_score": float(f1_score(targets, preds, average="weighted", zero_division=0)),
        "best_epoch": int(best_epoch),
        "best_val_loss": float(best_val_loss),
    }
    logger.info(
        "Test  acc=%.4f  prec=%.4f  rec=%.4f  f1=%.4f",
        metrics["accuracy"], metrics["precision"],
        metrics["recall"], metrics["f1_score"],
    )

    # ── model complexity ───────────────────────────────────────────────────────
    sample_x, _ = next(iter(test_loader))
    sample_x = sample_x[:1].to(device)
    model_path = result_paths["models"] / "best_model.pth"
    complexity = _measure_model_complexity(model, sample_x, model_path, device)

    # ── JSON outputs ───────────────────────────────────────────────────────────
    _json_dump(result_paths["json"] / "metrics.json", metrics)
    _json_dump(result_paths["json"] / "config.json", config.to_json_dict())
    _json_dump(
        result_paths["json"] / "training_history.json",
        {"model_name": config.model_name, "best_epoch": best_epoch, "history": history},
    )
    _json_dump(
        result_paths["json"] / "confusion_matrix_data.json",
        {
            "model_name": config.model_name,
            "y_true": [int(v) for v in targets],
            "y_pred": [int(v) for v in preds],
        },
    )
    _json_dump(result_paths["json"] / "model_analysis.json", complexity)

    logger.info("Results written to %s", result_paths["json"])
    return metrics
