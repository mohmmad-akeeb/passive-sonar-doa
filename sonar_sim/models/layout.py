"""Tensor layout helpers.

Generated data is stored as ``(batch, time, sensors)``. Several models were
written for ``(batch, sensors, time)``.
"""

from __future__ import annotations

import torch


def to_sensor_major(x: torch.Tensor, n_sensors: int = 32) -> torch.Tensor:
    """Return ``(batch, sensors, time)`` regardless of the incoming layout."""
    if x.dim() != 3:
        return x
    if x.size(1) == n_sensors:
        return x
    if x.size(2) == n_sensors:
        return x.permute(0, 2, 1).contiguous()
    return x
