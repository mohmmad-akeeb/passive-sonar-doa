"""Assemble Y = S + Z for one towed-array observation."""

from __future__ import annotations

from dataclasses import dataclass
import logging

import numpy as np
from numpy.typing import NDArray

from sonar_sim.generation.array import simulate_ula
from sonar_sim.generation.config import SimulationConfig
from sonar_sim.generation.sources import ambient_noise, bandpass_taps, source_waveform

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    """One array observation and its constituent fields."""

    received: NDArray[np.floating]
    target: NDArray[np.floating]
    interference_plus_noise: NDArray[np.floating]
    target_bearing_deg: float
    sinr_db: float
    broadband: bool


class PassiveSonarSimulator:
    """Thesis ADM mixer: self-noise at 15°, target at a chosen bearing."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self._taps = bandpass_taps(self.config.signal, self.config.array.sample_rate_hz)

    def _spatial_source(
        self,
        *,
        snr_db: float,
        bearing_deg: float,
        tone_frequency_hz: float,
        bearing_increment_deg: float,
    ) -> NDArray[np.floating]:
        cfg = self.config
        n_frame = int(cfg.array.sample_rate_hz) + cfg.signal.fir_order
        frames: list[NDArray[np.floating]] = []
        bearing = float(bearing_deg)

        for _ in range(cfg.duration_s):
            waveform = source_waveform(
                n_frame,
                cfg.array,
                cfg.signal,
                broadband=cfg.broadband,
                tone_frequency_hz=tone_frequency_hz,
                rng=self._rng,
                taps=self._taps,
            )
            snapshot = simulate_ula(waveform, bearing, cfg.array, cfg.signal)
            frames.append(snapshot[cfg.signal.fir_order :])
            bearing += bearing_increment_deg

        stacked = np.concatenate(frames, axis=0)
        amplitude = 10.0 ** (snr_db / 20.0)
        return amplitude * stacked

    def generate_snapshot(self, target_bearing_deg: float) -> Snapshot:
        cfg = self.config
        logger.debug(
            "Generating snapshot bearing=%.1f° BB=%s SINR=%.1f dB",
            target_bearing_deg,
            cfg.broadband,
            cfg.sinr_db,
        )

        interference = self._spatial_source(
            snr_db=cfg.interference_snr_db,
            bearing_deg=cfg.signal.interference_bearing_deg,
            tone_frequency_hz=cfg.signal.self_noise_frequency_hz,
            bearing_increment_deg=0.0,
        )
        target = self._spatial_source(
            snr_db=cfg.target_snr_db,
            bearing_deg=target_bearing_deg,
            tone_frequency_hz=cfg.signal.target_frequency_hz,
            bearing_increment_deg=cfg.target_bearing_increment_deg,
        )

        interference_plus_noise = interference
        if cfg.add_ambient_noise:
            noise = ambient_noise(
                interference.shape[0],
                cfg.array.n_sensors,
                self._taps,
                self._rng,
            )
            interference_plus_noise = interference + noise

        received = target + interference_plus_noise
        return Snapshot(
            received=received,
            target=target,
            interference_plus_noise=interference_plus_noise,
            target_bearing_deg=float(target_bearing_deg),
            sinr_db=cfg.sinr_db,
            broadband=cfg.broadband,
        )
