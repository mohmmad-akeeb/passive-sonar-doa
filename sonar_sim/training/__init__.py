"""Load snapshots, train a model, and persist metrics."""

from sonar_sim.training.config import TrainConfig
from sonar_sim.training.data import build_loaders
from sonar_sim.training.trainer import create_results_dir, train_and_evaluate

__all__ = ["TrainConfig", "build_loaders", "create_results_dir", "train_and_evaluate"]
