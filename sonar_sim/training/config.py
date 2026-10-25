from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# @dataclass automatically generates methods like __init__() using the class fields.
@dataclass
class TrainConfig:
    seed: int = 42
    data_dir: Path = Path("data")
    signal_file: str = "noisy.npy"
    labels_file: str = "labels.npy"
    results_dir: Path = Path("results")
    model_name: str = "cnn_gru"
    num_classes: int = 181
    num_sensors: int = 32
    smoothing: float = 0.1
    radius: int = 1
    endfire_ranges: tuple[tuple[int, int], ...] = ((0, 30), (150, 180))
    copies: int = 4
    train_ratio: float = 0.6
    val_ratio: float = 0.2
    test_ratio: float = 0.2
    noise_std: float = 0.05
    batch_size_train: int = 16
    batch_size_val: int = 16
    batch_size_test: int = 256
    num_workers: int = 4
    epochs: int = 200
    learning_rate: float = 1e-3
    patience: int = 25
    scheduler_patience: int = 7
    scheduler_factor: float = 0.5
    # field(default_factory=dict) creates a separate empty dictionary for each instance,
    # avoiding shared mutable default values.
    model_kwargs: dict = field(default_factory=dict)

    def to_json_dict(self) -> dict:
        # self.__dict__ returns a dictionary containing the object's instance attributes and their current values.
        # dict(self.__dict__)  Creates a shallow copy of that dictionary.
        payload = dict(self.__dict__)
        payload["data_dir"] = str(self.data_dir)
        payload["results_dir"] = str(self.results_dir)
        payload["endfire_ranges"] = [list(pair) for pair in self.endfire_ranges]
        return payload
