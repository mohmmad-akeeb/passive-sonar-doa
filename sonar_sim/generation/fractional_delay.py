"""Two-tap LMMSE interpolator and integer-plus-fractional delay filter.

Ported from the thesis ``int_fil`` / ``delay`` MATLAB→Python pair. Frequency
arguments may be in Hz or kHz; only the ratios ``f / fs`` matter.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.signal import lfilter

_EPS = np.finfo(float).eps


def interpolation_taps(
    f_low: float,
    f_high: float,
    sample_rate: float,
    fractional_delay: float,
) -> NDArray[np.floating]:
    """Return the two FIR taps that realize a fractional sample delay."""
    bandwidth = np.pi * (f_high - f_low) / sample_rate
    center = np.pi * (f_high + f_low) / sample_rate
    w_frac = bandwidth * fractional_delay
    c_frac = center * fractional_delay

    off_diag = np.cos(center) * np.sin(bandwidth) / bandwidth
    gram = np.array([[1.0, off_diag], [off_diag, 1.0]], dtype=np.float64)
    rhs = np.array(
        [
            np.cos(c_frac) * np.sin(w_frac + _EPS) / (w_frac + _EPS),
            np.cos(center - c_frac) * np.sin(bandwidth - w_frac + _EPS)
            / (bandwidth - w_frac + _EPS),
        ],
        dtype=np.float64,
    )
    return np.linalg.solve(gram, rhs)


def delay_signal(
    signal: NDArray[np.floating],
    sample_delay: float,
    f_low: float,
    f_high: float,
    sample_rate: float,
) -> NDArray[np.floating]:
    """Apply a (possibly fractional) delay via a short interpolation FIR."""
    integer_delay = int(np.floor(sample_delay))
    fractional = float(sample_delay - integer_delay)
    taps = interpolation_taps(f_low, f_high, sample_rate, fractional)

    impulse = np.zeros(integer_delay + 2, dtype=np.float64)
    impulse[integer_delay : integer_delay + 2] = taps
    return lfilter(impulse, 1.0, signal)
