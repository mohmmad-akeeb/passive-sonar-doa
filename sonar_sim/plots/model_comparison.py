"""Bar-chart comparisons of accuracy, precision, recall, and F1 across models.

Reads ``comparison_results.json`` written by ``sonar_sim.training.benchmark``.

CLI
---
    python -m sonar_sim.plots.model_comparison \\
        --results results/comparison/comparison_results.json \\
        --out figures/model_comparison.png

JSON schema consumed
--------------------
    {
      "cnn_gru": {
        "model_name": "cnn_gru",
        "accuracy":   0.91,
        "precision":  0.90,
        "recall":     0.91,
        "f1_score":   0.90,
        "best_epoch": 42,
        "model_analysis": {
          "total_parameters": 123456,
          "learnable_parameters": 123456,
          "flops": 1e8,
          "inference_time_ms": 2.1,
          "model_size_mb": 1.5
        }
      },
      ...
    }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from sonar_sim.plots.utils import (
    METRIC_DISPLAY_NAMES,
    apply_style,
    model_color,
    model_label,
    percent_axis,
    save_figure,
)

_COMPARISON_METRICS = ["accuracy", "precision", "recall", "f1_score"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_comparison(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


# ── grouped bar chart ─────────────────────────────────────────────────────────

def plot_model_comparison(
    comparison_path: str | Path,
    out_path: str | Path = "figures/model_comparison.png",
    *,
    metrics: list[str] | None = None,
    show: bool = False,
) -> Path:
    """Grouped bar chart of classification metrics across all models.

    Parameters
    ----------
    comparison_path:
        Path to ``comparison_results.json`` from the benchmark runner.
    out_path:
        Destination image path.
    metrics:
        Subset of metrics to show. Defaults to accuracy/precision/recall/F1.
    show:
        If True, call ``plt.show()`` in addition to saving.
    """
    apply_style()
    metrics = metrics or _COMPARISON_METRICS
    data = _load_comparison(comparison_path)

    model_names = list(data.keys())
    values = {m: [] for m in metrics}
    for name in model_names:
        for m in metrics:
            values[m].append(float(data[name].get(m, 0.0)))

    n_models = len(model_names)
    n_metrics = len(metrics)
    x = np.arange(n_models)
    bar_w = 0.8 / n_metrics

    fig, ax = plt.subplots(figsize=(max(8, n_models * 1.6), 5))

    for i, metric in enumerate(metrics):
        offsets = x + (i - n_metrics / 2 + 0.5) * bar_w
        bars = ax.bar(
            offsets, values[metric], bar_w * 0.9,
            label=METRIC_DISPLAY_NAMES.get(metric, metric),
            alpha=0.88,
        )
        # value labels on top of bars
        for bar, v in zip(bars, values[metric]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{v:.3f}",
                ha="center", va="bottom", fontsize=7,
            )

    ax.set_xticks(x)
    ax.set_xticklabels([model_label(n) for n in model_names], rotation=15, ha="right")
    ax.set_ylabel("Score")
    ax.set_title("Model Comparison — Classification Metrics", fontsize=14, fontweight="bold")
    percent_axis(ax)
    ax.legend(loc="lower right")
    fig.tight_layout()

    out = save_figure(fig, out_path, close=not show)
    if show:
        plt.show()
        plt.close(fig)
    return out


# ── per-metric individual plots ───────────────────────────────────────────────

def plot_metric_bars(
    comparison_path: str | Path,
    out_dir: str | Path = "figures",
    *,
    show: bool = False,
) -> list[Path]:
    """One horizontal bar chart per metric, coloured by model.

    Produces four files: accuracy.png, precision.png, recall.png, f1_score.png.
    """
    apply_style()
    data = _load_comparison(comparison_path)
    out_dir = Path(out_dir)
    saved: list[Path] = []

    for metric in _COMPARISON_METRICS:
        model_names = list(data.keys())
        vals = [float(data[n].get(metric, 0.0)) for n in model_names]
        colors = [model_color(n, i) for i, n in enumerate(model_names)]

        fig, ax = plt.subplots(figsize=(6, 0.7 * len(model_names) + 1.5))
        y = np.arange(len(model_names))
        bars = ax.barh(y, vals, color=colors, alpha=0.88)

        for bar, v in zip(bars, vals):
            ax.text(
                v + 0.003, bar.get_y() + bar.get_height() / 2,
                f"{v:.4f}", va="center", fontsize=9,
            )

        ax.set_yticks(y)
        ax.set_yticklabels([model_label(n) for n in model_names])
        ax.set_xlabel("Score")
        ax.set_xlim(0, 1.08)
        ax.set_title(
            METRIC_DISPLAY_NAMES.get(metric, metric),
            fontsize=13, fontweight="bold",
        )
        fig.tight_layout()
        out = save_figure(fig, out_dir / f"{metric}.png", close=not show)
        saved.append(out)
        if show:
            plt.show()

    return saved


# ── complexity summary table plot ─────────────────────────────────────────────

def plot_complexity_table(
    comparison_path: str | Path,
    out_path: str | Path = "figures/complexity_table.png",
    *,
    show: bool = False,
) -> Path:
    """Render model complexity metrics (params, FLOPs, latency, size) as a table figure."""
    apply_style()
    data = _load_comparison(comparison_path)

    rows = []
    col_labels = ["Model", "Params (M)", "FLOPs (G)", "Latency (ms)", "Size (MB)"]
    for name, entry in data.items():
        ana = entry.get("model_analysis") or {}
        params_m = (ana.get("learnable_parameters") or 0) / 1e6
        flops_g = (ana.get("flops") or 0) / 1e9
        latency = ana.get("inference_time_ms") or float("nan")
        size_mb = ana.get("model_size_mb") or float("nan")
        rows.append([
            model_label(name),
            f"{params_m:.2f}",
            f"{flops_g:.2f}" if flops_g else "—",
            f"{latency:.2f}",
            f"{size_mb:.2f}" if size_mb else "—",
        ])

    fig, ax = plt.subplots(figsize=(9, 0.5 * len(rows) + 1.8))
    ax.axis("off")
    tbl = ax.table(
        cellText=rows,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.2, 1.6)

    # header row styling
    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor("#0072B2")
        tbl[0, j].set_text_props(color="white", fontweight="bold")

    # alternating row shading
    for i in range(1, len(rows) + 1):
        bg = "#f0f4f8" if i % 2 == 0 else "white"
        for j in range(len(col_labels)):
            tbl[i, j].set_facecolor(bg)

    ax.set_title("Model Complexity Summary", fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    out = save_figure(fig, out_path, close=not show)
    if show:
        plt.show()
        plt.close(fig)
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Plot model comparison charts.")
    p.add_argument("--results", required=True,
                   help="Path to comparison_results.json.")
    p.add_argument("--out", default="figures/model_comparison.png",
                   help="Output path for grouped bar chart.")
    p.add_argument("--out-dir", default="figures",
                   help="Output directory for per-metric and complexity plots.")
    p.add_argument("--show", action="store_true")
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    out1 = plot_model_comparison(args.results, args.out, show=args.show)
    print(f"Saved grouped chart: {out1}")
    saved = plot_metric_bars(args.results, args.out_dir, show=args.show)
    for s in saved:
        print(f"Saved metric chart: {s}")
    out_tbl = plot_complexity_table(
        args.results,
        Path(args.out_dir) / "complexity_table.png",
        show=args.show,
    )
    print(f"Saved complexity table: {out_tbl}")


if __name__ == "__main__":
    main()
