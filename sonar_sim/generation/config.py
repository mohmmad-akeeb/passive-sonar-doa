"""ULA geometry and signal parameters matching the thesis simulator."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArrayConfig:
    """Uniform linear array designed to Nyquist at the upper frequency."""

    n_sensors: int = 32
    sound_speed_mps: float = 1500.0
    design_frequency_hz: float = 4000.0
    sample_rate_hz: float = 4096.0

    @property
    def element_spacing_m(self) -> float:
        return self.sound_speed_mps / (2.0 * self.design_frequency_hz) 


@dataclass(frozen=True)
class SignalConfig:
    """Narrowband (BB0) tones and wideband (BB1) cavitation profile."""

    start_frequency_hz: float = 100.0
    end_frequency_hz: float = 2000.0
    fir_order: int = 512
    self_noise_frequency_hz: float = 1200.0
    target_frequency_hz: float = 1300.0
    am_index: float = 0.5
    am_frequencies_hz: tuple[float, float] = (5.0, 10.0)
    interference_bearing_deg: float = 15.0
    tone_amplitude: float = 1.0


@dataclass
class SimulationConfig:
    """One simulation run: BB0/BB1, SINR, duration, and RNG seed."""

    array: ArrayConfig = field(default_factory=ArrayConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    broadband: bool = False
    sinr_db: float = -30.0
    interference_snr_db: float = 20.0
    duration_s: int = 1
    target_bearing_increment_deg: float = 0.0
    add_ambient_noise: bool = True
    seed: int | None = None

    @property
    def target_snr_db(self) -> float:
        return self.sinr_db + self.interference_snr_db
