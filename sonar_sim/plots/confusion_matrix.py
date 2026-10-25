"""Plot a confusion matrix from ``confusion_matrix_data.json``.

For 181-class DOA the full matrix is visually dense.  This module renders:
  1. A full 181×181 heatmap (with angular ticks every 30°).
  2. A diagonal accuracy ribbon — the fraction of predictions within ±N° of
     truth — which is the most informative metric for continuous DOA.
  3. Per-bearing accuracy bar chart (useful to spot endfire performance).

CLI
---
    python -m sonar_sim.plots.confusion_matrix \\
        --cm results/comparison/cnn_gru/.../json/confusion_matrix_data.json \\
        --out figures/cnn_gru_cm.png

JSON schema consumed
--------------------
    {
      "model_name": "cnn_gru",   # optional
      "y_true": [90, 45, ...],
      "y_pred": [91, 44, ...]
    }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

from sonar_sim.plots.utils import apply_style, model_label, save_figure


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_cm_data(path: str | Path) -> tuple[list[int], list[int], str]:
    with Path(path).open(encoding="utf-8") as fh:
        d = json.load(fh)
    return d["y_true"], d["y_pred"], d.get("model_name", "")


def _within_n_deg_accuracy(y_true: np.ndarray, y_pred: np.ndarray, n: int) -> float:
    return float(np.mean(np.abs(y_true - y_pred) <= n))


# ── full confusion matrix heatmap ─────────────────────────────────────────────

def plot_confusion_matrix(
    cm_path: str | Path,
    out_path: str | Path = "figures/confusion_matrix.png",
    *,
    num_classes: int = 181,
    show: bool = False,
) -> Path:
    """181×181 heatmap with major ticks every 30°.

    Parameters
    ----------
    cm_path:
        Path to ``confusion_matrix_data.json``.
    out_path:
        Destination image path.
    num_classes:
        Number of bearing classes (default 181 for 0°–180°).
    show:
        If True, display interactively in addition to saving.
    """
    apply_style()
    y_true, y_pred, model_name = _load_cm_data(cm_path)

    labels = list(range(num_classes))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    # normalise row-wise so each cell = P(predicted | truth)
    row_sums = cm.sum(axis=1, keepdims=True).clip(min=1)
    cm_norm = cm.astype(np.float32) / row_sums

    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(cm_norm, aspect="auto", cmap="Blues", vmin=0, vmax=1,
                   origin="upper", interpolation="nearest")
    fig.colorbar(im, ax=ax, fraction=0.035, label="P(predicted | truth)")

    tick_step = 30
    ticks = list(range(0, num_classes, tick_step))
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([f"{t}°" for t in ticks])
    ax.set_yticklabels([f"{t}°" for t in ticks])
    ax.set_xlabel("Predicted Bearing (°)")
    ax.set_ylabel("True Bearing (°)")

    title = "Confusion Matrix"
    if model_name:
        title += f" — {model_label(model_name)}"
    acc_1 = _within_n_deg_accuracy(np.array(y_true), np.array(y_pred), 1)
    acc_5 = _within_n_deg_accuracy(np.array(y_true), np.array(y_pred), 5)
    ax.set_title(f"{title}\nAcc±1°: {acc_1:.1%}  |  Acc±5°: {acc_5:.1%}",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()

    out = save_figure(fig, out_path, close=not show)
    if show:
        plt.show()
        plt.close(fig)
    return out


# ── diagonal accuracy ribbon ──────────────────────────────────────────────────

def plot_diagonal_accuracy(
    cm_path: str | Path,
    out_path: str | Path = "figures/diagonal_accuracy.png",
    *,
    tolerances: list[int] | None = None,
    show: bool = False,
) -> Path:
    """Plot Acc±N° as a function of tolerance N (1 – 15 degrees).

    This is the most compact and meaningful summary for a continuous DOA task.
    """
    apply_style()
    y_true, y_pred, model_name = _load_cm_data(cm_path)
    yt = np.array(y_true)
    yp = np.array(y_pred)

    tolerances = tolerances or list(range(1, 16))
    accs = [_within_n_deg_accuracy(yt, yp, n) for n in tolerances]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(tolerances, accs, "o-", color="#0072B2", linewidth=2)
    ax.fill_between(tolerances, accs, alpha=0.15, color="#0072B2")
    for n, a in zip(tolerances, accs):
        if n in (1, 3, 5, 10):
            ax.annotate(f"{a:.1%}", (n, a), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=8)
    ax.set_xlabel("Tolerance (°)")
    ax.set_ylabel("Accuracy within ±N°")
    ax.set_xticks(tolerances)
    ax.set_ylim(0, 1.05)
    title = "Diagonal Accuracy (Acc ±N°)"
    if model_name:
        title += f" — {model_label(model_name)}"
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.tight_layout()

    out = save_figure(fig, out_path, close=not show)
    if show:
        plt.show()
        plt.close(fig)
    return out


# ── per-bearing accuracy bar chart ────────────────────────────────────────────

def plot_per_bearing_accuracy(
    cm_path: str | Path,
    out_path: str | Path = "figures/per_bearing_accuracy.png",
    *,
    tolerance: int = 1,
    show: bool = False,
) -> Path:
    """Bar chart of per-bearing Acc±tolerance.

    Quickly reveals endfire (0°/180°) vs broadside (90°) performance gaps.
    """
    apply_style()
    y_true, y_pred, model_name = _load_cm_data(cm_path)
    yt = np.array(y_true)
    yp = np.array(y_pred)

    bearings = sorted(set(yt.tolist()))
    per_bearing_acc = []
    for b in bearings:
        mask = yt == b
        if mask.sum() == 0:
            per_bearing_acc.append(float("nan"))
        else:
            per_bearing_acc.append(float(np.mean(np.abs(yp[mask] - b) <= tolerance)))

    fig, ax = plt.subplots(figsize=(12, 4))
    bars = ax.bar(bearings, per_bearing_acc, width=0.9, color="#0072B2", alpha=0.8)
    # colour endfire regions differently
    for bar, b in zip(bars, bearings):
        if b <= 30 or b >= 150:
            bar.set_color("#D55E00")

    ax.set_xlabel("True Bearing (°)")
    ax.set_ylabel(f"Acc ±{tolerance}°")
    ax.set_ylim(0, 1.1)
    ax.set_xticks(range(0, 181, 15))
    title = f"Per-Bearing Accuracy (±{tolerance}°)"
    if model_name:
        title += f" — {model_label(model_name)}"
    ax.set_title(title, fontsize=12, fontweight="bold")
    # legend for endfire colouring
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#0072B2", alpha=0.8, label="Broadside (31°–149°)"),
        Patch(facecolor="#D55E00", alpha=0.8, label="Endfire (0°–30°, 150°–180°)"),
    ]
    ax.legend(handles=legend_elements, fontsize=8, loc="lower center")
    fig.tight_layout()

    out = save_figure(fig, out_path, close=not show)
    if show:
        plt.show()
        plt.close(fig)
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Plot confusion matrix and related charts.")
    p.add_argument("--cm", required=True, help="Path to confusion_matrix_data.json.")
    p.add_argument("--out", default="figures/confusion_matrix.png")
    p.add_argument("--out-dir", default="figures",
                   help="Directory for diagonal accuracy and per-bearing charts.")
    p.add_argument("--tolerance", type=int, default=1,
                   help="Degree tolerance for per-bearing bar chart.")
    p.add_argument("--show", action="store_true")
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    out_dir = Path(args.out_dir)
    out1 = plot_confusion_matrix(args.cm, args.out, show=args.show)
    print(f"Saved: {out1}")
    out2 = plot_diagonal_accuracy(args.cm, out_dir / "diagonal_accuracy.png", show=args.show)
    print(f"Saved: {out2}")
    out3 = plot_per_bearing_accuracy(
        args.cm, out_dir / "per_bearing_accuracy.png",
        tolerance=args.tolerance, show=args.show,
    )
    print(f"Saved: {out3}")


if __name__ == "__main__":
    main()
