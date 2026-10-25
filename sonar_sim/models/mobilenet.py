import torch
import torch.nn as nn

class DepthwiseSeparableBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int, use_hswish: bool = False) -> None:
        super().__init__()
        self.dw = nn.Sequential(
            nn.Conv2d(
                in_channels,
                in_channels,
                kernel_size=3,
                stride=stride,
                padding=1,
                groups=in_channels,
                bias=False,
            ),
            nn.BatchNorm2d(in_channels),
            nn.Hardswish() if use_hswish else nn.ReLU(inplace=True),
        )
        self.pw = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.Hardswish() if use_hswish else nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.pw(self.dw(x))


class ModifiedMobileNet(nn.Module):
    """Expects spectrograms ``(batch, sensors, 224, 224)`` or raw time series."""

    def __init__(self, num_sensors: int = 32, num_classes: int = 181) -> None:
        super().__init__()
        self.num_sensors = num_sensors
        self.init_conv = nn.Sequential(
            nn.Conv2d(num_sensors, 32, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.Hardswish(),
        )
        self.blocks = nn.Sequential(
            DepthwiseSeparableBlock(32, 64, stride=1, use_hswish=False),
            DepthwiseSeparableBlock(64, 128, stride=2, use_hswish=False),
            DepthwiseSeparableBlock(128, 256, stride=2, use_hswish=False),
            DepthwiseSeparableBlock(256, 512, stride=2, use_hswish=True),
            DepthwiseSeparableBlock(512, 512, stride=1, use_hswish=True),
            DepthwiseSeparableBlock(512, 1024, stride=2, use_hswish=True),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Linear(1024, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 3:
            raise ValueError(
                "ModifiedMobileNet expects spectrograms of shape "
                "(batch, sensors, 224, 224). Use the training spectrogram transform."
            )
        x = self.init_conv(x)
        x = self.blocks(x)
        return self.classifier(self.avgpool(x).flatten(1))
