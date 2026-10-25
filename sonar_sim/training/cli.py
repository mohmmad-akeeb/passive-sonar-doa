"""``python -m sonar_sim.training --model cnn_gru --data-dir data``."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import torch

from sonar_sim.models.factory import MODEL_NAMES
from sonar_sim.training.config import TrainConfig
from sonar_sim.training.data import build_loaders
from sonar_sim.training.trainer import create_results_dir, train_and_evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a DOA classifier on generated ULA data.")
    parser.add_argument("--model", choices=MODEL_NAMES, default="cnn_gru")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--signal-file", default="noisy.npy")
    parser.add_argument("--labels-file", default="labels.npy")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=4)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    config = TrainConfig(
        seed=args.seed,
        data_dir=args.data_dir,
        signal_file=args.signal_file,
        labels_file=args.labels_file,
        results_dir=args.results_dir,
        model_name=args.model,
        epochs=args.epochs,
        batch_size_train=args.batch_size,
        batch_size_val=args.batch_size,
        learning_rate=args.lr,
        num_workers=args.num_workers,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logging.getLogger(__name__).info("Device %s | model %s", device, config.model_name)
    result_paths = create_results_dir(config.results_dir, config.model_name)
    loaders = build_loaders(config)
    train_and_evaluate(config, *loaders, device, result_paths)


if __name__ == "__main__":
    main()
