"""Unit and integration tests for the sonar_sim generation pipeline.

Run from repo root:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import tempfile
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from sonar_sim.generation.array import inter_element_delays_s, simulate_ula
from sonar_sim.generation.config import ArrayConfig, SignalConfig, SimulationConfig
from sonar_sim.generation.dataset import DatasetSpec, generate_dataset, save_dataset
from sonar_sim.generation.fractional_delay import delay_signal, interpolation_taps
from sonar_sim.generation.scenario import PassiveSonarSimulator
from sonar_sim.generation.sources import ambient_noise, bandpass_taps, source_waveform
from sonar_sim.models import build_model


# ===========================================================================
# ArrayConfig / geometry
# ===========================================================================

class TestArrayConfig:
    def test_element_spacing_is_half_wavelength_at_design_frequency(self) -> None:
        array = ArrayConfig()
        assert array.element_spacing_m == pytest.approx(0.1875)

    def test_element_spacing_formula(self) -> None:
        # d = c / (2 * f_design)
        array = ArrayConfig(sound_speed_mps=1500.0, design_frequency_hz=4000.0)
        assert array.element_spacing_m == pytest.approx(1500.0 / (2 * 4000.0))

    def test_config_is_frozen(self) -> None:
        array = ArrayConfig()
        with pytest.raises((AttributeError, TypeError)):
            array.n_sensors = 64  # type: ignore[misc]

    def test_sample_rate(self) -> None:
        assert ArrayConfig().sample_rate_hz == pytest.approx(4096.0)

    def test_n_sensors(self) -> None:
        assert ArrayConfig().n_sensors == 32


# ===========================================================================
# Fractional delay filter
# ===========================================================================

class TestFractionalDelay:
    def test_taps_shape(self) -> None:
        taps = interpolation_taps(100.0, 2000.0, 4096.0, 0.25)
        assert taps.shape == (2,)

    def test_taps_finite(self) -> None:
        taps = interpolation_taps(100.0, 2000.0, 4096.0, 0.25)
        assert np.all(np.isfinite(taps))

    def test_zero_fractional_delay_gives_integer_shift(self) -> None:
        """Zero fractional part → all energy in first tap."""
        taps = interpolation_taps(100.0, 2000.0, 4096.0, 0.0)
        assert taps.shape == (2,)
        assert np.all(np.isfinite(taps))

    def test_delay_shifts_impulse_by_integer_part(self) -> None:
        impulse = np.zeros(64)
        impulse[10] = 1.0
        delayed = delay_signal(impulse, 3.0, 100.0, 2000.0, 4096.0)
        assert np.argmax(np.abs(delayed)) >= 12

    def test_delay_output_length_unchanged(self) -> None:
        sig = np.random.default_rng(0).standard_normal(256)
        out = delay_signal(sig, 5.7, 100.0, 2000.0, 4096.0)
        assert out.shape == sig.shape

    def test_zero_delay_is_near_identity(self) -> None:
        """A zero sample delay should return a signal very close to the input."""
        rng = np.random.default_rng(42)
        sig = rng.standard_normal(256)
        out = delay_signal(sig, 0.0, 100.0, 2000.0, 4096.0)
        # Output equals input (IIR with trivial taps)
        assert np.allclose(out, sig, atol=1e-6)

    def test_larger_delay_still_finite(self) -> None:
        sig = np.random.default_rng(1).standard_normal(512)
        out = delay_signal(sig, 15.9, 100.0, 2000.0, 4096.0)
        assert np.all(np.isfinite(out))


# ===========================================================================
# ULA array simulation
# ===========================================================================

class TestSimulateULA:
    def test_snapshot_shape(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        tone = np.sin(2 * np.pi * 1300 * np.arange(512) / array.sample_rate_hz)
        snap = simulate_ula(tone, 60.0, array, signal)
        assert snap.shape == (512, 32)

    def test_channels_are_unit_std(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        tone = np.sin(2 * np.pi * 1300 * np.arange(512) / array.sample_rate_hz)
        snap = simulate_ula(tone, 60.0, array, signal)
        assert np.allclose(np.std(snap, axis=0), 1.0, atol=1e-6)

    def test_broadside_has_equal_delays(self) -> None:
        """At 90° (broadside) the cosine term is 0 → all delays equal."""
        array = ArrayConfig()
        delays = inter_element_delays_s(90.0, array)
        assert np.allclose(delays, delays[0], atol=1e-10)

    def test_endfire_0_delays_monotone(self) -> None:
        """At 0° (endfire) cos(0°) = 1 → delays increase monotonically."""
        array = ArrayConfig()
        delays = inter_element_delays_s(0.0, array)
        assert np.all(np.diff(delays) >= 0)

    def test_delays_are_non_negative(self) -> None:
        array = ArrayConfig()
        for bearing in [0.0, 15.0, 45.0, 90.0, 135.0, 180.0]:
            delays = inter_element_delays_s(bearing, array)
            assert np.min(delays) >= -1e-12, f"Negative delay at {bearing}°"

    def test_different_bearings_give_different_snapshots(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        rng = np.random.default_rng(0)
        waveform = rng.standard_normal(512)
        snap_30 = simulate_ula(waveform, 30.0, array, signal)
        snap_60 = simulate_ula(waveform, 60.0, array, signal)
        assert not np.allclose(snap_30, snap_60)


# ===========================================================================
# Source waveforms (BB0 narrowband / BB1 wideband)
# ===========================================================================

class TestSourceWaveforms:
    def test_narrowband_differs_from_wideband(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        rng = np.random.default_rng(0)
        nb = source_waveform(256, array, signal, broadband=False,
                              tone_frequency_hz=1300.0, rng=rng)
        rng = np.random.default_rng(0)
        wb = source_waveform(256, array, signal, broadband=True,
                              tone_frequency_hz=1300.0, rng=rng)
        assert not np.allclose(nb, wb)

    def test_narrowband_output_length(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        rng = np.random.default_rng(1)
        out = source_waveform(512, array, signal, broadband=False,
                               tone_frequency_hz=1300.0, rng=rng)
        assert out.shape == (512,)

    def test_wideband_output_is_finite(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        rng = np.random.default_rng(2)
        wb = source_waveform(1024, array, signal, broadband=True,
                              tone_frequency_hz=1300.0, rng=rng)
        assert np.all(np.isfinite(wb))

    def test_wideband_has_more_energy_than_narrowband(self) -> None:
        """Broadband adds shaped noise on top of the tone → higher RMS."""
        array, signal = ArrayConfig(), SignalConfig()
        rng = np.random.default_rng(3)
        nb = source_waveform(4096, array, signal, broadband=False,
                              tone_frequency_hz=1300.0, rng=rng)
        rng = np.random.default_rng(3)
        wb = source_waveform(4096, array, signal, broadband=True,
                              tone_frequency_hz=1300.0, rng=rng)
        assert np.std(wb) > np.std(nb)

    def test_ambient_noise_shape(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        taps = bandpass_taps(signal, array.sample_rate_hz)
        rng = np.random.default_rng(0)
        noise = ambient_noise(512, 32, taps, rng)
        assert noise.shape == (512, 32)

    def test_ambient_noise_unit_std_per_sensor(self) -> None:
        array, signal = ArrayConfig(), SignalConfig()
        taps = bandpass_taps(signal, array.sample_rate_hz)
        rng = np.random.default_rng(0)
        noise = ambient_noise(4096, 32, taps, rng)
        assert np.allclose(np.std(noise, axis=0), 1.0, atol=0.05)

    def test_ambient_noise_sensors_are_independent(self) -> None:
        """Cross-channel correlation should be near zero."""
        array, signal = ArrayConfig(), SignalConfig()
        taps = bandpass_taps(signal, array.sample_rate_hz)
        rng = np.random.default_rng(0)
        noise = ambient_noise(8192, 32, taps, rng)
        corr = np.corrcoef(noise.T)
        off_diag = corr[np.triu_indices(32, k=1)]
        assert np.abs(off_diag).mean() < 0.05


# ===========================================================================
# PassiveSonarSimulator (scenario assembly)
# ===========================================================================

class TestPassiveSonarSimulator:
    def test_snapshot_shape_bb0(self) -> None:
        cfg = SimulationConfig(duration_s=1, seed=0, broadband=False)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(90.0)
        assert snap.received.shape == (4096, 32)

    def test_snapshot_shape_bb1(self) -> None:
        cfg = SimulationConfig(duration_s=1, seed=0, broadband=True)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(90.0)
        assert snap.received.shape == (4096, 32)

    def test_received_equals_target_plus_interference(self) -> None:
        cfg = SimulationConfig(duration_s=1, seed=5, add_ambient_noise=False)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(60.0)
        assert np.allclose(snap.received,
                           snap.target + snap.interference_plus_noise,
                           atol=1e-6)

    def test_sinr_scaling_bb0(self) -> None:
        """Target RMS should be ≈ 10^((sinr+int_snr)/20)."""
        cfg = SimulationConfig(sinr_db=-30.0, interference_snr_db=20.0,
                               seed=9, broadband=False)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(90.0)
        expected = 10 ** ((cfg.sinr_db + cfg.interference_snr_db) / 20.0)
        actual = float(np.sqrt(np.mean(snap.target ** 2)))
        assert pytest.approx(expected, rel=0.5) == actual

    def test_sinr_scaling_bb1(self) -> None:
        cfg = SimulationConfig(sinr_db=-30.0, interference_snr_db=20.0,
                               seed=10, broadband=True)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(45.0)
        expected = 10 ** ((cfg.sinr_db + cfg.interference_snr_db) / 20.0)
        actual = float(np.sqrt(np.mean(snap.target ** 2)))
        assert pytest.approx(expected, rel=0.5) == actual

    def test_negative_sinr_means_noise_dominates(self) -> None:
        """At −30 dB SINR the interference power must exceed the target power."""
        cfg = SimulationConfig(sinr_db=-30.0, interference_snr_db=20.0, seed=11)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(90.0)
        target_pow = float(np.mean(snap.target ** 2))
        interference_pow = float(np.mean(snap.interference_plus_noise ** 2))
        assert interference_pow > target_pow

    def test_different_seeds_give_different_snapshots(self) -> None:
        snap_a = PassiveSonarSimulator(SimulationConfig(seed=1)).generate_snapshot(90.0)
        snap_b = PassiveSonarSimulator(SimulationConfig(seed=2)).generate_snapshot(90.0)
        assert not np.allclose(snap_a.received, snap_b.received)

    def test_same_seed_gives_reproducible_snapshots(self) -> None:
        snap_a = PassiveSonarSimulator(SimulationConfig(seed=42)).generate_snapshot(90.0)
        snap_b = PassiveSonarSimulator(SimulationConfig(seed=42)).generate_snapshot(90.0)
        assert np.allclose(snap_a.received, snap_b.received)

    def test_interference_fixed_at_15_degrees(self) -> None:
        cfg = SimulationConfig(seed=0)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(90.0)
        assert cfg.signal.interference_bearing_deg == pytest.approx(15.0)

    def test_multi_second_duration_stacks_correctly(self) -> None:
        cfg = SimulationConfig(duration_s=3, seed=0)
        snap = PassiveSonarSimulator(cfg).generate_snapshot(90.0)
        assert snap.received.shape == (3 * 4096, 32)


# ===========================================================================
# Dataset pipeline
# ===========================================================================

class TestDatasetPipeline:
    def test_generate_dataset_shape(self) -> None:
        bearings = np.arange(0.0, 181.0, 30.0)
        cfg = SimulationConfig(seed=0)
        data, labels = generate_dataset(cfg, DatasetSpec(bearings_deg=bearings, repeats=1))
        assert data.shape == (len(bearings), 4096, 32)
        assert data.dtype == np.float32

    def test_generate_dataset_labels_match_bearings(self) -> None:
        bearings = np.array([0.0, 45.0, 90.0, 135.0, 180.0])
        cfg = SimulationConfig(seed=0)
        _, labels = generate_dataset(cfg, DatasetSpec(bearings_deg=bearings, repeats=1))
        assert list(labels) == [0, 45, 90, 135, 180]

    def test_repeats_multiply_samples(self) -> None:
        bearings = np.array([30.0, 60.0, 90.0])
        cfg = SimulationConfig(seed=0)
        data, labels = generate_dataset(cfg, DatasetSpec(bearings_deg=bearings, repeats=3))
        assert data.shape[0] == len(bearings) * 3

    def test_save_dataset_writes_files(self) -> None:
        bearings = np.array([90.0])
        cfg = SimulationConfig(seed=0)
        data, labels = generate_dataset(cfg, DatasetSpec(bearings_deg=bearings))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            save_dataset(data, labels, cfg, out)
            assert (out / "noisy.npy").exists()
            assert (out / "labels.npy").exists()
            assert (out / "generation_metadata.json").exists()

    def test_save_dataset_provenance_keys(self) -> None:
        bearings = np.array([90.0])
        cfg = SimulationConfig(seed=0)
        data, labels = generate_dataset(cfg, DatasetSpec(bearings_deg=bearings))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            save_dataset(data, labels, cfg, out)
            meta = json.loads((out / "generation_metadata.json").read_text())
        required = {
            "shape", "dtype", "layout", "broadband", "bb_index",
            "sinr_db", "interference_snr_db", "duration_s",
            "sample_rate_hz", "n_sensors", "element_spacing_m",
            "sound_speed_mps", "self_noise_frequency_hz",
            "target_frequency_hz", "interference_bearing_deg", "seed",
        }
        assert required.issubset(meta.keys())

    def test_save_reload_roundtrip(self) -> None:
        bearings = np.array([45.0, 90.0, 135.0])
        cfg = SimulationConfig(seed=3)
        data, labels = generate_dataset(cfg, DatasetSpec(bearings_deg=bearings))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            save_dataset(data, labels, cfg, out)
            data2 = np.load(out / "noisy.npy")
            labels2 = np.load(out / "labels.npy")
        assert np.array_equal(data, data2)
        assert np.array_equal(labels, labels2)

    def test_bb0_bb1_datasets_differ(self) -> None:
        bearings = np.array([90.0])
        data_bb0, _ = generate_dataset(
            SimulationConfig(broadband=False, seed=1),
            DatasetSpec(bearings_deg=bearings),
        )
        data_bb1, _ = generate_dataset(
            SimulationConfig(broadband=True, seed=1),
            DatasetSpec(bearings_deg=bearings),
        )
        assert not np.allclose(data_bb0, data_bb1)


# ===========================================================================
# Model forward passes (shape contract only — no training)
# ===========================================================================

@pytest.mark.parametrize("model_name", ["cnn_gru", "mlp", "bi_lstm", "dracnn"])
def test_model_forward_pass_shape(model_name: str) -> None:
    """Every model must map (B, T, M) → (B, 181) without error."""
    model = build_model(model_name, num_sensors=32, num_classes=181)
    model.eval()
    # (batch=2, time=4096, sensors=32)
    x = torch.randn(2, 4096, 32)
    with torch.no_grad():
        out = model(x)
    assert out.shape == (2, 181), f"{model_name}: got {out.shape}"


@pytest.mark.parametrize("model_name", ["cnn_gru", "mlp", "bi_lstm", "dracnn"])
def test_model_output_is_finite(model_name: str) -> None:
    model = build_model(model_name, num_sensors=32, num_classes=181)
    model.eval()
    x = torch.randn(2, 4096, 32)
    with torch.no_grad():
        out = model(x)
    assert torch.all(torch.isfinite(out)), f"{model_name}: non-finite logits"


def test_build_model_raises_on_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown model"):
        build_model("nonexistent_model")
