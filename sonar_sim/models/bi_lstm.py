import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from sonar_sim.models.layout import to_sensor_major


def get_sonar_sinc_filters(
    out_channels: int,
    kernel_size: int,
    num_sensors: int = 32,
    sample_rate: int = 8000,
    fmin: float = 100.0,
    fmax: float = 2000.0,
) -> torch.Tensor:
    num_filters = out_channels // num_sensors
    hz_points = np.linspace(fmin, fmax, num_filters + 2)
    f1 = hz_points[:-2]
    f2 = hz_points[2:]
    t = np.linspace(-(kernel_size // 2), kernel_size // 2, kernel_size)
    base_weights = np.zeros((num_filters, 1, kernel_size), dtype=np.float32)
    for i in range(num_filters):
        low = 2 * (f2[i] / sample_rate) * np.sinc(2 * (f2[i] / sample_rate) * t)
        high = 2 * (f1[i] / sample_rate) * np.sinc(2 * (f1[i] / sample_rate) * t)
        band = (low - high) * np.hamming(kernel_size)
        band /= np.linalg.norm(band) + 1e-8
        base_weights[i, 0, :] = band
    return torch.tensor(np.tile(base_weights, (num_sensors, 1, 1)))


class SoftAttention(nn.Module):
    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Softmax(dim=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weights = self.attention(x)
        return torch.sum(weights * x, dim=1)


class EndToEndSonarClassifier(nn.Module):
    def __init__(
        self,
        num_sensors: int = 32,
        num_classes: int = 181,
        num_filters: int = 64,
        kernel_size: int = 251,
        lstm_layers: int = 3,
        lstm_hidden: int = 128,
    ) -> None:
        super().__init__()
        self.num_sensors = num_sensors
        self.filterbank = nn.Conv1d(
            in_channels=num_sensors,
            out_channels=num_sensors * num_filters,
            kernel_size=kernel_size,
            padding=kernel_size // 2,
            groups=num_sensors,
        )
        self.filterbank.weight.data = get_sonar_sinc_filters(
            out_channels=num_sensors * num_filters,
            kernel_size=kernel_size,
        )
        self.pool1d = nn.MaxPool1d(kernel_size=3)
        self.spectro_temporal_blocks = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(0.1),
            nn.MaxPool2d(kernel_size=2),
            nn.Dropout(0.2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.1),
            nn.MaxPool2d(kernel_size=2),
            nn.Dropout(0.2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.1),
            nn.MaxPool2d(kernel_size=2),
            nn.Dropout(0.2),
        )
        self.freq_pool = nn.AdaptiveAvgPool2d((1, 64))
        self.blstm = nn.LSTM(
            input_size=128,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=False,
        )
        self.attention = SoftAttention(hidden_dim=lstm_hidden)
        self.classifier = nn.Sequential(
            nn.Linear(lstm_hidden, 64),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = to_sensor_major(x, self.num_sensors)
        x = self.pool1d(F.relu(self.filterbank(x)))
        x = torch.log(torch.clamp(torch.abs(x), min=1e-6))
        x = self.spectro_temporal_blocks(x.unsqueeze(1))
        x = self.freq_pool(x).squeeze(2).permute(0, 2, 1)
        x, _ = self.blstm(x)
        return self.classifier(self.attention(x))
