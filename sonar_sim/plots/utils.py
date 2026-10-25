"""Shared matplotlib style, colour palette, and save helpers.

All plotting modules import from here so visual consistency is enforced in
one place.  Call ``apply_style()`` at the top of any plotting function.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── palette ───────────────────────────────────────────────────────────────────
# One distinct colour per model — colour-blind-safe (Wong 2011)
MODEL_COLORS: dict[str, str] = {
    "cnn_gru":   "#0072B2",   # blue
    "bi_lstm":   "#E69F00",   # amber
    "dracnn":    "#009E73",   # green
    "mlp":       "#D55E00",   # vermillion
    "mobilenet": "#CC79A7",   # pink
}
_FALLBACK_COLORS = ["#56B4E9", "#F0E442", "#000000", "#999999"]

MODEL_DISPLAY_NAMES: dict[str, str] = {
    "cnn_gru":   "CNN-GRU",
    "bi_lstm":   "Bi-LSTM",
    "dracnn":    "DRACNN",
    "mlp":       "MLP",
    "mobilenet": "MobileNet",
}

METRIC_DISPLAY_NAMES: dict[str, str] = {
    "accuracy":  "Accuracy",
    "precision": "Precision",
    "recall":    "Recall",
    "f1_score":  "F1 Score",
}


def model_color(name: str, idx: int = 0) -> str:
    """Return the canonical colour for *name*, falling back gracefully."""
    key = name.lower().replace("-", "_")
    return MODEL_COLORS.get(key, _FALLBACK_COLORS[idx % len(_FALLBACK_COLORS)])


def model_label(name: str) -> str:
    key = name.lower().replace("-", "_")
    return MODEL_DISPLAY_NAMES.get(key, name)


# ── style ─────────────────────────────────────────────────────────────────────

def apply_style() -> None:
    """Apply a clean, publication-quality rcParams style."""
    matplotlib.rcParams.update({
        # fonts
        "font.family":       "sans-serif",
        "font.size":         11,
        "axes.titlesize":    13,
        "axes.labelsize":    11,
        "xtick.labelsize":   9,
        "ytick.labelsize":   9,
        "legend.fontsize":   9,
        # lines & markers
        "lines.linewidth":   1.8,
        "lines.markersize":  4,
        # axes
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.grid":         True,
        "grid.alpha":        0.3,
        "grid.linestyle":    "--",
        # figure
        "figure.dpi":        150,
        "savefig.dpi":       300,
        "savefig.bbox":      "tight",
    })


# ── save helper ───────────────────────────────────────────────────────────────

def save_figure(fig: plt.Figure, path: str | Path, *, close: bool = True) -> Path:
    """Save *fig* to *path* (auto-creates parent dirs) and optionally close it."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    if close:
        plt.close(fig)
    return out


# ── axis helpers ──────────────────────────────────────────────────────────────

def percent_axis(ax: plt.Axes) -> None:
    """Format the y-axis of *ax* as 0-100 % with a percent sign."""
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_ylim(0, 1.05)


def annotate_best_epoch(ax: plt.Axes, best_epoch: int, color: str = "#555555") -> None:
    """Draw a vertical dashed line at *best_epoch*."""
    ax.axvline(best_epoch, color=color, linestyle=":", linewidth=1.2,
               label=f"Best epoch ({best_epoch})")
