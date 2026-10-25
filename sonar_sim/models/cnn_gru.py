import torch
import torch.nn as nn
import torch.nn.functional as F

from sonar_sim.models.layout import to_sensor_major


class GRUBlock(nn.Module):
    def __init__(self, d_model: int, state_dim: int = 128) -> None:
        super().__init__()
        self.core = nn.GRU(d_model, state_dim, batch_first=True)
        self.output_proj = nn.Linear(state_dim, d_model)
        self.layer_norm = nn.LayerNorm(d_model)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.core(x)
        out = self.output_proj(out)
        return self.activation(self.layer_norm(out + x))


class AttentionPool(nn.Module):
    """Soft attention over the time axis — preserves more variance than mean pooling."""

    def __init__(self, d_model: int) -> None:
        super().__init__()
        self.attn = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, d_model)
        weights = F.softmax(self.attn(x), dim=1)   # (B, T, 1)
        return (weights * x).sum(dim=1)             # (B, d_model)


class CNN_GRU(nn.Module):
    def __init__(
        self,
        num_sensors: int = 32,
        d_model: int = 128,
        n_layers: int = 2,
        num_classes: int = 181,
    ) -> None:
        super().__init__()
        self.num_sensors = num_sensors

        # InstanceNorm1d normalises per-sample, per-channel — works correctly
        # on the first batch unlike BatchNorm1d which needs running stat warmup.
        self.feature_extractor = nn.Sequential(
            nn.Conv1d(num_sensors, d_model, kernel_size=32, stride=8, padding=16),
            nn.InstanceNorm1d(d_model, affine=True),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Conv1d(d_model, d_model, kernel_size=8, stride=2, padding=4),
            nn.InstanceNorm1d(d_model, affine=True),
            nn.GELU(),
        )
        self.ssm_layers = nn.ModuleList(
            [GRUBlock(d_model=d_model, state_dim=256) for _ in range(n_layers)]
        )
        self.pool = AttentionPool(d_model)
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 256),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = to_sensor_major(x, self.num_sensors)   # (B, M, T)
        x = self.feature_extractor(x)              # (B, d_model, T')
        x = x.permute(0, 2, 1)                     # (B, T', d_model)
        for layer in self.ssm_layers:
            x = layer(x)
        x = self.pool(x)                            # (B, d_model)
        return self.head(x)                         # (B, num_classes)
