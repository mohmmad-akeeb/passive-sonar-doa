"""Passive-SONAR simulation, models, and training for ULA direction finding."""

from sonar_sim.generation.config import ArrayConfig, SignalConfig, SimulationConfig
from sonar_sim.generation.dataset import DatasetSpec, generate_dataset, save_dataset
from sonar_sim.generation.scenario import PassiveSonarSimulator, Snapshot
from sonar_sim.models.factory import build_model
from sonar_sim.models.losses import SoftCrossEntropyLoss

__all__ = [
    # Configuration
    "ArrayConfig",
    "SignalConfig",
    "SimulationConfig",
    # Data generation
    "PassiveSonarSimulator",
    "Snapshot",
    "DatasetSpec",
    "generate_dataset",
    "save_dataset",
    # Models
    "build_model",
    "SoftCrossEntropyLoss",
    # Plots (imported lazily — only available when matplotlib is installed)
]
