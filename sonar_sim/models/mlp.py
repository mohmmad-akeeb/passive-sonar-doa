import torch
import torch.nn as nn

from sonar_sim.models.layout import to_sensor_major


class NUMP(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.pool1 = nn.MaxPool1d(kernel_size=2, stride=2)
        self.pool2 = nn.MaxPool1d(kernel_size=8, stride=8)
        self.pool3 = nn.MaxPool1d(kernel_size=16, stride=16)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = x.unsqueeze(1)
        p1 = self.pool1(x[:, :, :256]).squeeze(1)
        p2 = self.pool2(x[:, :, 256:512]).squeeze(1)
        p3 = self.pool3(x[:, :, 512:2048]).squeeze(1)
        return torch.cat([p1, p2, p3], dim=1), p1


class LightweightSonarMLP(nn.Module):
    def __init__(self, num_sensors: int = 32, num_classes: int = 181) -> None:
        super().__init__()
        self.num_sensors = num_sensors
        self.nump = NUMP()
        self.mlp = nn.Sequential(
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
        )
        self.norm = nn.LayerNorm(128)
        self.classifier = nn.Linear(256, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = to_sensor_major(x, self.num_sensors)
        fft_mag = torch.log1p(torch.abs(torch.fft.fft(x, n=4096, dim=2)[:, :, :2048]))
        fft_mag = fft_mag.reshape(fft_mag.shape[0], -1)
        fft_mag = (fft_mag - fft_mag.mean(dim=1, keepdim=True)) / (
            fft_mag.std(dim=1, keepdim=True) + 1e-8
        )
        nump_out, skip_conn = self.nump(fft_mag)
        concat_feat = torch.cat([skip_conn, self.norm(self.mlp(nump_out))], dim=1)
        return self.classifier(concat_feat)
