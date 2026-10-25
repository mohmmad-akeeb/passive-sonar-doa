"""Scalar source waveforms: tones (BB0) and AM-modulated broadband (BB1)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.signal import firwin, lfilter

from sonar_sim.generation.config import ArrayConfig, SignalConfig


def bandpass_taps(signal: SignalConfig, sample_rate_hz: float) -> NDArray[np.floating]:
    return firwin(
        signal.fir_order,
        [signal.start_frequency_hz, signal.end_frequency_hz],
        fs=sample_rate_hz,
        pass_zero=False,
    )


def time_index(n_samples: int) -> NDArray[np.floating]:
    """1-based sample index used by the original MATLAB/Python ADM."""
    return np.arange(1, n_samples + 1, dtype=np.float64)


def source_waveform(
    n_samples: int,
    array: ArrayConfig,
    signal: SignalConfig,
    *,
    broadband: bool,
    tone_frequency_hz: float,
    rng: np.random.Generator,
    taps: NDArray[np.floating] | None = None,
) -> NDArray[np.floating]:
    """Build one FIR-length frame of the scalar source before spatialization.

    Wideband energy is amplitude-modulated at 5 Hz and 10 Hz. Narrowband mode
    keeps the same tones and zeros the broadband term (``BroadbandOnOff``).
    """
    taps = bandpass_taps(signal, array.sample_rate_hz) if taps is None else taps
    white = rng.standard_normal(n_samples)
    shaped = lfilter(taps, 1.0, white)

    n = time_index(n_samples)
    fs = array.sample_rate_hz
    f_mod1, f_mod2 = signal.am_frequencies_hz
    envelope = (
        1.0
        + signal.am_index * np.sin(2.0 * np.pi * f_mod1 / fs * n)
        + signal.am_index * np.sin(2.0 * np.pi * f_mod2 / fs * n)
    )
    broadband_term = envelope * shaped * float(broadband)
    tone = signal.tone_amplitude * np.sin(2.0 * np.pi * tone_frequency_hz / fs * n)
    return broadband_term + tone


def ambient_noise(
    n_samples: int,
    n_sensors: int,
    taps: NDArray[np.floating],
    rng: np.random.Generator,
) -> NDArray[np.floating]:
    """Independent per-sensor unit-power bandpass Gaussian noise."""
    white = rng.standard_normal((n_samples, n_sensors))
    colored = lfilter(taps, 1.0, white, axis=0)
    std = np.std(colored, axis=0, keepdims=True)
    std = np.where(std == 0.0, 1.0, std)
    return colored / std
