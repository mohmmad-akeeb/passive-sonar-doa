"""Plot training / validation loss and accuracy curves.

Reads ``training_history.json`` produced by ``sonar_sim.training.trainer``.

CLI
---
    # single model run
    python -m sonar_sim.plots.learning_curves \\
        --history results/comparison/cnn_gru/20260101_120000/json/training_history.json \\
        --out figures/cnn_gru_curves.png

    # overlay multiple models (pass several --history flags)
    python -m sonar_sim.plots.learning_curves \\
        --history results/comparison/cnn_gru/.../json/training_history.json \\
        --history results/comparison/mlp/.../json/training_history.json \\
        --out figures/all_curves.png

JSON schema expected
--------------------
    {
      "model_name": "cnn_gru",      # optional — used for legend label
      "best_epoch": 42,             # optional — draws a vertical marker
      "history": {
        "epoch":      [1, 2, ...],
        "train_loss": [...],
        "val_loss":   [...],
        "train_acc":  [...],
        "val_acc":    [...]
      }
    }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from sonar_sim.plots.utils import (
    annotate_best_epoch,
    apply_style,
    model_color,
    model_label,
    percent_axis,
    save_figure,
)


# ── core plotting function ────────────────────────────────────────────────────

def plot_learning_curves(
    history_paths: list[str | Path],
    out_path: str | Path = "figures/learning_curves.png",
    *,
    show: bool = False,
) -> Path:
    """Plot loss and accuracy curves from one or more ``training_history.json`` files.

    Parameters
    ----------
    history_paths:
        List of paths to ``training_history.json`` files.
    out_path:
        Destination image path.
    show:
        If True, call ``plt.show()`` in addition to saving.

    Returns
    -------
    Path to the saved figure.
    """
    apply_style()

    records: list[dict] = []
    for p in history_paths:
        with Path(p).open(encoding="utf-8") as fh:
            records.append(json.load(fh))

    multi = len(records) > 1
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ax_loss, ax_acc = axes

    for idx, rec in enumerate(records):
        h = rec["history"]
        name = rec.get("model_name", f"model_{idx}")
        best = rec.get("best_epoch")
        color = model_color(name, idx)
        label = model_label(name)
        epochs = h.get("epoch") or list(range(1, len(h["train_loss"]) + 1))

        # loss
        ax_loss.plot(epochs, h["train_loss"], color=color,
                     linestyle="-",  label=f"{label} train" if multi else "Train")
        ax_loss.plot(epochs, h["val_loss"],   color=color,
                     linestyle="--", label=f"{label} val"   if multi else "Validation")
        if best and not multi:
            annotate_best_epoch(ax_loss, best)

        # accuracy
        ax_acc.plot(epochs, h["train_acc"], color=color,
                    linestyle="-",  label=f"{label} train" if multi else "Train")
        ax_acc.plot(epochs, h["val_acc"],   color=color,
                    linestyle="--", label=f"{label} val"   if multi else "Validation")
        if best and not multi:
            annotate_best_epoch(ax_acc, best)

    ax_loss.set_title("Loss")
    ax_loss.set_xlabel("Epoch")
    ax_loss.set_ylabel("Cross-Entropy Loss")
    ax_loss.legend()

    ax_acc.set_title("Accuracy")
    ax_acc.set_xlabel("Epoch")
    ax_acc.set_ylabel("Accuracy")
    percent_axis(ax_acc)
    ax_acc.legend()

    title = "Learning Curves"
    if not multi and records:
        title = f"Learning Curves — {model_label(records[0].get('model_name', ''))}"
    fig.suptitle(title, fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()

    out = save_figure(fig, out_path, close=not show)
    if show:
        plt.show()
        plt.close(fig)
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Plot learning curves from training_history.json.")
    p.add_argument("--history", dest="history_paths", action="append", required=True,
                   metavar="PATH",
                   help="Path to training_history.json (repeat for multiple models).")
    p.add_argument("--out", default="figures/learning_curves.png",
                   help="Output image path.")
    p.add_argument("--show", action="store_true", help="Display the figure interactively.")
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    out = plot_learning_curves(args.history_paths, args.out, show=args.show)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
