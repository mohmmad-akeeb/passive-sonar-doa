from __future__ import annotations

import torch.nn as nn

from sonar_sim.models.bi_lstm import EndToEndSonarClassifier
from sonar_sim.models.cnn_gru import CNN_GRU
from sonar_sim.models.dracnn import DOACNN
from sonar_sim.models.mlp import LightweightSonarMLP
from sonar_sim.models.mobilenet import ModifiedMobileNet

MODEL_NAMES = ("cnn_gru", "mlp", "bi_lstm", "dracnn", "mobilenet")


def build_model(name: str, num_sensors: int = 32, num_classes: int = 181, **kwargs) -> nn.Module:
    key = name.lower().replace("-", "_")
    if key == "cnn_gru":
        return CNN_GRU(
            num_sensors=num_sensors,
            d_model=int(kwargs.get("d_model", 64)),
            n_layers=int(kwargs.get("n_layers", 1)),
            num_classes=num_classes,
        )
    if key == "mlp":
        return LightweightSonarMLP(num_sensors=num_sensors, num_classes=num_classes)
    if key in {"bi_lstm", "lstm"}:
        return EndToEndSonarClassifier(
            num_sensors=num_sensors,
            num_classes=num_classes,
            num_filters=int(kwargs.get("num_filters", 64)),
            kernel_size=int(kwargs.get("kernel_size", 251)),
            lstm_layers=int(kwargs.get("lstm_layers", 3)),
            lstm_hidden=int(kwargs.get("lstm_hidden", 128)),
        )
    if key == "dracnn":
        return DOACNN(num_sensors=num_sensors, num_classes=num_classes)
    if key == "mobilenet":
        return ModifiedMobileNet(num_sensors=num_sensors, num_classes=num_classes)
    raise ValueError(f"Unknown model '{name}'. Choose from {MODEL_NAMES}.")
