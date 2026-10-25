"""Synthetic ULA snapshot generation (thesis physics pipeline)."""

from sonar_sim.generation.config import ArrayConfig, SignalConfig, SimulationConfig
from sonar_sim.generation.dataset import DatasetSpec, generate_dataset, save_dataset
from sonar_sim.generation.scenario import PassiveSonarSimulator, Snapshot

__all__ = [
    "ArrayConfig",
    "SignalConfig",
    "SimulationConfig",
    "PassiveSonarSimulator",
    "Snapshot",
    "DatasetSpec",
    "generate_dataset",
    "save_dataset",
]
