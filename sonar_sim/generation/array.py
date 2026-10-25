"""Propagate a scalar waveform across the ULA with sub-sample delays."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from sonar_sim.generation.config import ArrayConfig, SignalConfig
from sonar_sim.generation.fractional_delay import delay_signal

_EPS = np.finfo(float).eps


def inter_element_delays_s(
    bearing_deg: float,
    array: ArrayConfig,
) -> NDArray[np.floating]:
    """Geometric delay τ_m = m · d · cos(θ) / c, shifted to be non-negative."""
    sensor_index = np.arange(array.n_sensors, dtype=np.float64)
    tau = sensor_index * (
        array.element_spacing_m * np.cos(np.deg2rad(bearing_deg)) / array.sound_speed_mps
    )
    # Thesis simulate_ULA: shift by max|τ| so every channel delay is ≥ 0.
    return tau + np.max(np.abs(tau))


def simulate_ula(
    waveform: NDArray[np.floating],
    bearing_deg: float,
    array: ArrayConfig,
    signal: SignalConfig,
) -> NDArray[np.floating]:
    """Return a ``(n_samples, n_sensors)`` snapshot of ``waveform`` on the ULA.

    Each channel is delay-interpolated then normalized to unit sample standard
    deviation, matching ``simulate_ULA`` in the thesis code.
    """
    sample_delays = inter_element_delays_s(bearing_deg, array) * array.sample_rate_hz
    n_samples = waveform.shape[0]
    snapshot = np.empty((n_samples, array.n_sensors), dtype=np.float64)

    for sensor, delay in enumerate(sample_delays):
        delayed = delay_signal(
            waveform,
            float(delay),
            signal.start_frequency_hz,
            signal.end_frequency_hz,
            array.sample_rate_hz,
        )
        snapshot[:, sensor] = delayed / (np.std(delayed) + _EPS)

    return snapshot
