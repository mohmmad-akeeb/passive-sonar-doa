import torch
import torch.nn as nn

from sonar_sim.models.layout import to_sensor_major


class DOACNN(nn.Module):
    def __init__(self, num_sensors: int = 32, num_classes: int = 181) -> None:
        super().__init__()
        self.num_sensors = num_sensors
        self.sensor_frontend = nn.Sequential(
            nn.Conv1d(
                in_channels=num_sensors,
                out_channels=num_sensors * 4,
                kernel_size=251,
                padding=125,
                groups=num_sensors,
            ),
            nn.BatchNorm1d(num_sensors * 4),
            nn.ReLU(),
        )
        self.features = nn.Sequential(
            nn.Conv1d(128, 64, kernel_size=7, padding=3),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Conv1d(64, 64, kernel_size=7, padding=3),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(64, 128, kernel_size=5, padding=2),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Conv1d(128, 128, kernel_size=5, padding=2),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Dropout(0.2),
            nn.Conv1d(128, 256, kernel_size=5, padding=2),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Conv1d(256, 256, kernel_size=5, padding=2),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = to_sensor_major(x, self.num_sensors)
        x = self.sensor_frontend(x)
        x = self.features(x)
        return self.classifier(x)
