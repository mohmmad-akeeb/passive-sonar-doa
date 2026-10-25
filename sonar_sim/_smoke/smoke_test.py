"""Runnable smoke validation for the generation pipeline.

Usage (from repo root):
    python -m sonar_sim._smoke.smoke_test

Checks performed:
  - BB0 (narrowband) snapshot: shape, dtype, SINR amplitude scaling
  - BB1 (wideband) snapshot: shape, dtype, broadband energy > tonal energy
  - Dataset pipeline: generate_dataset produces correct (N, T, M) tensor
  - Provenance JSON written and keys present
  - Target energy > interference energy after SINR scaling (sign-of-life physics check)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

# Allow running as `python sonar_sim/_smoke/smoke_test.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sonar_sim.generation.config import ArrayConfig, SignalConfig, SimulationConfig
from sonar_sim.generation.dataset import DatasetSpec, generate_dataset, save_dataset
from sonar_sim.generation.scenario import PassiveSonarSimulator

PYTHON = sys.executable
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {PASS}  {name}")
    else:
        msg = f"{name}" + (f" — {detail}" if detail else "")
        print(f"  {FAIL}  {msg}")
        _failures.append(msg)


# ---------------------------------------------------------------------------
# 1. BB0 snapshot (narrowband)
# ---------------------------------------------------------------------------
print("\n[1] BB0 narrowband snapshot")
cfg_bb0 = SimulationConfig(broadband=False, sinr_db=-30.0, interference_snr_db=20.0, seed=1)
sim_bb0 = PassiveSonarSimulator(cfg_bb0)
snap_bb0 = sim_bb0.generate_snapshot(target_bearing_deg=90.0)

n_time = int(cfg_bb0.array.sample_rate_hz)
n_sens = cfg_bb0.array.n_sensors

check("received shape", snap_bb0.received.shape == (n_time, n_sens),
      f"got {snap_bb0.received.shape}")
check("target shape matches received", snap_bb0.received.shape == snap_bb0.target.shape)
check("received is finite", np.all(np.isfinite(snap_bb0.received)))
check("broadband flag is False", snap_bb0.broadband is False)
check("bearing stored correctly", snap_bb0.target_bearing_deg == 90.0)

# SINR scaling: target amplitude ≈ 10^((sinr_db + int_snr_db)/20)
expected_target_amp = 10 ** ((cfg_bb0.sinr_db + cfg_bb0.interference_snr_db) / 20.0)
actual_target_rms = float(np.sqrt(np.mean(snap_bb0.target ** 2)))
check(
    "target RMS within 3 dB of expected amplitude",
    0.5 * expected_target_amp < actual_target_rms < 2.0 * expected_target_amp,
    f"expected≈{expected_target_amp:.4f} got {actual_target_rms:.4f}",
)

# ---------------------------------------------------------------------------
# 2. BB1 snapshot (wideband)
# ---------------------------------------------------------------------------
print("\n[2] BB1 wideband snapshot")
cfg_bb1 = SimulationConfig(broadband=True, sinr_db=-30.0, interference_snr_db=20.0, seed=2)
sim_bb1 = PassiveSonarSimulator(cfg_bb1)
snap_bb1 = sim_bb1.generate_snapshot(target_bearing_deg=45.0)

check("received shape", snap_bb1.received.shape == (n_time, n_sens),
      f"got {snap_bb1.received.shape}")
check("broadband flag is True", snap_bb1.broadband is True)
check("received is finite", np.all(np.isfinite(snap_bb1.received)))

# Wideband target must differ from narrowband target at same seed/bearing
snap_nb_same = PassiveSonarSimulator(
    SimulationConfig(broadband=False, sinr_db=-30.0, seed=2)
).generate_snapshot(45.0)
check(
    "BB1 received != BB0 received (wideband energy present)",
    not np.allclose(snap_bb1.received, snap_nb_same.received),
)

# ---------------------------------------------------------------------------
# 3. Dataset pipeline — generate_dataset
# ---------------------------------------------------------------------------
print("\n[3] Dataset pipeline (generate_dataset)")
bearings = np.array([0.0, 45.0, 90.0, 135.0, 180.0])
cfg_ds = SimulationConfig(broadband=False, sinr_db=-20.0, seed=7)
spec = DatasetSpec(bearings_deg=bearings, repeats=2)
data, labels = generate_dataset(cfg_ds, spec)

n_expected = len(bearings) * spec.repeats
check("dataset N samples", data.shape[0] == n_expected, f"got {data.shape[0]}")
check("dataset time axis", data.shape[1] == n_time, f"got {data.shape[1]}")
check("dataset sensor axis", data.shape[2] == n_sens, f"got {data.shape[2]}")
check("dataset dtype float32", data.dtype == np.float32, f"got {data.dtype}")
check("labels length matches N", len(labels) == n_expected)
check("labels dtype int16", labels.dtype == np.int16, f"got {labels.dtype}")
check("labels cover all bearings", set(labels.tolist()) == {int(b) for b in bearings})
check("data is finite", bool(np.all(np.isfinite(data))))

# ---------------------------------------------------------------------------
# 4. save_dataset — provenance JSON
# ---------------------------------------------------------------------------
print("\n[4] Provenance JSON (save_dataset)")
required_keys = {
    "shape", "dtype", "layout", "broadband", "bb_index",
    "sinr_db", "interference_snr_db", "duration_s",
    "sample_rate_hz", "n_sensors", "element_spacing_m",
    "sound_speed_mps", "self_noise_frequency_hz",
    "target_frequency_hz", "interference_bearing_deg", "seed",
}
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp)
    save_dataset(data, labels, cfg_ds, out)
    check("noisy.npy written", (out / "noisy.npy").exists())
    check("labels.npy written", (out / "labels.npy").exists())
    check("generation_metadata.json written", (out / "generation_metadata.json").exists())
    meta = json.loads((out / "generation_metadata.json").read_text())
    missing = required_keys - meta.keys()
    check("all provenance keys present", len(missing) == 0, f"missing: {missing}")
    check("provenance shape matches", meta["shape"] == list(data.shape))
    check("provenance bb_index correct", meta["bb_index"] == int(cfg_ds.broadband))

# ---------------------------------------------------------------------------
# 5. Physics sign-of-life: interference power >> target power (high SINR Z)
# ---------------------------------------------------------------------------
print("\n[5] Physics sign-of-life (highly negative SINR)")
cfg_snr = SimulationConfig(broadband=False, sinr_db=-30.0, interference_snr_db=20.0, seed=3)
snap_snr = PassiveSonarSimulator(cfg_snr).generate_snapshot(60.0)
target_power = float(np.mean(snap_snr.target ** 2))
noise_power  = float(np.mean(snap_snr.interference_plus_noise ** 2))
sinr_actual  = 10.0 * np.log10(target_power / (noise_power + 1e-12))
check(
    "actual SINR is negative (target buried in noise)",
    sinr_actual < 0.0,
    f"SINR = {sinr_actual:.1f} dB",
)
print(f"         measured SINR ≈ {sinr_actual:.1f} dB  (configured: {cfg_snr.sinr_db} dB)")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if _failures:
    print(f"SMOKE FAILED — {len(_failures)} check(s) failed:")
    for f in _failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    total = 22  # count of check() calls above
    print(f"ALL SMOKE CHECKS PASSED ({total} checks)")
    sys.exit(0)
