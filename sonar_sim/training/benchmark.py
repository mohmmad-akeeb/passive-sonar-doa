"""Run all (or selected) models on one dataset and write a consolidated
comparison JSON used by the plotting utilities.

Usage
-----
    python -m sonar_sim.training.benchmark \\
        --data-dir data/bb1 \\
        --models cnn_gru mlp bi_lstm dracnn \\
        --results-dir results/comparison \\
        --epochs 200

Outputs (inside --results-dir)
-------------------------------
    <model>/<timestamp>/json/metrics.json          -- per-model metrics
    <model>/<timestamp>/json/training_history.json -- per-model curves
    <model>/<timestamp>/json/confusion_matrix_data.json
    <model>/<timestamp>/json/model_analysis.json   -- FLOPs, params, latency
    comparison_results.json                        -- aggregated summary
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import torch

from sonar_sim.models.factory import MODEL_NAMES
from sonar_sim.training.config import TrainConfig
from sonar_sim.training.data import build_loaders
from sonar_sim.training.trainer import create_results_dir, train_and_evaluate

logger = logging.getLogger(__name__)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Benchmark multiple DOA models on the same dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--models",
        nargs="+",
        choices=list(MODEL_NAMES) + ["all"],
        default=["all"],
        help="Models to evaluate. 'all' runs every available model.",
    )
    p.add_argument("--data-dir", type=Path, default=Path("data"),
                   help="Directory containing noisy.npy and labels.npy.")
    p.add_argument("--signal-file", default="noisy.npy")
    p.add_argument("--labels-file", default="labels.npy")
    p.add_argument("--results-dir", type=Path, default=Path("results/comparison"))
    p.add_argument("--epochs", type=int, default=200)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--num-workers", type=int, default=4)
    p.add_argument("-v", "--verbose", action="store_true")
    return p


# ── aggregation helper ────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _build_comparison(results_dir: Path, model_run_paths: dict[str, Path]) -> dict:
    """Collect every model's metrics + analysis into one flat comparison dict."""
    comparison: dict[str, dict] = {}
    for model_name, run_root in model_run_paths.items():
        json_dir = run_root / "json"
        entry: dict = {"model_name": model_name}

        metrics_file = json_dir / "metrics.json"
        if metrics_file.exists():
            entry.update(_load_json(metrics_file))

        analysis_file = json_dir / "model_analysis.json"
        if analysis_file.exists():
            entry["model_analysis"] = _load_json(analysis_file)

        history_file = json_dir / "training_history.json"
        if history_file.exists():
            h = _load_json(history_file)
            entry["best_epoch"] = h.get("best_epoch")
            entry["history_path"] = str(history_file)

        entry["results_root"] = str(run_root)
        comparison[model_name] = entry

    return comparison


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    models_to_run: list[str] = (
        list(MODEL_NAMES) if "all" in args.models else args.models
    )
    logger.info("Models to benchmark: %s", models_to_run)

    args.results_dir.mkdir(parents=True, exist_ok=True)
    model_run_paths: dict[str, Path] = {}

    for model_name in models_to_run:
        logger.info("=" * 60)
        logger.info("Starting model: %s", model_name)
        logger.info("=" * 60)

        config = TrainConfig(
            seed=args.seed,
            data_dir=args.data_dir,
            signal_file=args.signal_file,
            labels_file=args.labels_file,
            results_dir=args.results_dir,
            model_name=model_name,
            epochs=args.epochs,
            batch_size_train=args.batch_size,
            batch_size_val=args.batch_size,
            learning_rate=args.lr,
            num_workers=args.num_workers,
        )

        try:
            result_paths = create_results_dir(args.results_dir, model_name)
            loaders = build_loaders(config)
            metrics = train_and_evaluate(config, *loaders, device, result_paths)
            model_run_paths[model_name] = result_paths["root"]
            logger.info(
                "Finished %s — acc=%.4f  f1=%.4f",
                model_name, metrics["accuracy"], metrics["f1_score"],
            )
        except Exception as exc:
            logger.error("Model %s failed: %s", model_name, exc, exc_info=True)

    # ── write aggregated comparison JSON ─────────────────────────────────────
    if model_run_paths:
        comparison = _build_comparison(args.results_dir, model_run_paths)
        out_path = args.results_dir / "comparison_results.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(comparison, fh, indent=2)
        logger.info("Comparison results written to %s", out_path)
    else:
        logger.warning("No models completed successfully — comparison_results.json not written.")


if __name__ == "__main__":
    main()
