"""Driver script — generate every plot from dummy_data/ fixtures.

Outputs land in figures/  (auto-created).

Usage:
    python generate_plots.py
"""

from __future__ import annotations

from pathlib import Path

from sonar_sim.plots.learning_curves import plot_learning_curves
from sonar_sim.plots.model_comparison import (
    plot_complexity_table,
    plot_metric_bars,
    plot_model_comparison,
)
from sonar_sim.plots.confusion_matrix import (
    plot_confusion_matrix,
    plot_diagonal_accuracy,
    plot_per_bearing_accuracy,
)

DUMMY = Path("dummy_data")
FIG   = Path("figures")

MODEL_NAMES = ["cnn_gru", "bi_lstm", "dracnn", "mlp", "mobilenet"]

# ── 1. Learning curves ────────────────────────────────────────────────────────

# a) CNN-GRU alone — the hero chart
plot_learning_curves(
    [DUMMY / "training_history_cnn_gru.json"],
    out_path=FIG / "01_cnn_gru_learning_curves.png",
)
print("✓  01_cnn_gru_learning_curves.png")

# b) All five models overlaid — shows CNN-GRU converges fastest and highest
plot_learning_curves(
    [DUMMY / f"training_history_{m}.json" for m in MODEL_NAMES],
    out_path=FIG / "02_all_models_learning_curves.png",
)
print("✓  02_all_models_learning_curves.png")

# ── 2. Model comparison bar charts ───────────────────────────────────────────

# Grouped bar (accuracy / precision / recall / F1 side-by-side)
plot_model_comparison(
    DUMMY / "comparison_results.json",
    out_path=FIG / "03_model_comparison_grouped.png",
)
print("✓  03_model_comparison_grouped.png")

# Individual horizontal bar per metric
saved = plot_metric_bars(
    DUMMY / "comparison_results.json",
    out_dir=FIG,
)
for i, p in enumerate(saved, start=4):
    print(f"✓  0{i}_{p.name}")

# Complexity table (params / FLOPs / latency / size)
plot_complexity_table(
    DUMMY / "comparison_results.json",
    out_path=FIG / "08_complexity_table.png",
)
print("✓  08_complexity_table.png")

# ── 3. Confusion matrix suite (CNN-GRU) ───────────────────────────────────────

cm_path = DUMMY / "confusion_matrix_data_cnn_gru.json"

plot_confusion_matrix(
    cm_path,
    out_path=FIG / "09_cnn_gru_confusion_matrix.png",
)
print("✓  09_cnn_gru_confusion_matrix.png")

plot_diagonal_accuracy(
    cm_path,
    out_path=FIG / "10_cnn_gru_diagonal_accuracy.png",
)
print("✓  10_cnn_gru_diagonal_accuracy.png")

plot_per_bearing_accuracy(
    cm_path,
    out_path=FIG / "11_cnn_gru_per_bearing_accuracy.png",
    tolerance=1,
)
print("✓  11_cnn_gru_per_bearing_accuracy.png")

# ── summary ───────────────────────────────────────────────────────────────────
figures = sorted(FIG.glob("*.png"))
print(f"\nAll done — {len(figures)} figures written to {FIG.resolve()}/")
for f in figures:
    print(f"  {f.name}")
