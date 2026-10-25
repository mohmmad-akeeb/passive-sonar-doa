"""Sweep bearings and write float32 training tensors."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from sonar_sim.generation.config import SimulationConfig
from sonar_sim.generation.scenario import PassiveSonarSimulator

logger = logging.getLogger(__name__)


@dataclass
class DatasetSpec:
    bearings_deg: NDArray[np.floating]
    repeats: int = 1
    output_dir: Path = Path("data")


def generate_dataset(
    config: SimulationConfig,
    spec: DatasetSpec,
) -> tuple[NDArray[np.float32], NDArray[np.int16]]:
    """Return ``(N, T, M)`` received snapshots and integer bearing labels."""
    simulator = PassiveSonarSimulator(config)
    snapshots: list[NDArray[np.floating]] = []
    labels: list[int] = []

    n_total = int(spec.repeats * len(spec.bearings_deg))
    done = 0
    for _repeat in range(spec.repeats):
        for bearing in spec.bearings_deg:
            snap = simulator.generate_snapshot(float(bearing))
            snapshots.append(snap.received.astype(np.float32, copy=False))
            labels.append(int(np.rint(bearing)))
            done += 1
            if done % 20 == 0 or done == n_total:
                logger.info("Generated %d / %d snapshots", done, n_total)

    data = np.stack(snapshots, axis=0)
    label_array = np.asarray(labels, dtype=np.int16)
    return data, label_array


def save_dataset(
    data: NDArray[np.float32],
    labels: NDArray[np.integer],
    config: SimulationConfig,
    output_dir: Path,
) -> Path:
    """Write ``noisy.npy``, ``labels.npy``, and a JSON provenance file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "noisy.npy", data)
    np.save(output_dir / "labels.npy", np.asarray(labels))

    provenance = {
        "shape": list(data.shape),
        "dtype": str(data.dtype),
        "layout": "(n_samples, n_time, n_sensors)",
        "broadband": config.broadband,
        "bb_index": int(config.broadband),
        "sinr_db": config.sinr_db,
        "interference_snr_db": config.interference_snr_db,
        "duration_s": config.duration_s,
        "sample_rate_hz": config.array.sample_rate_hz,
        "n_sensors": config.array.n_sensors,
        "element_spacing_m": config.array.element_spacing_m,
        "sound_speed_mps": config.array.sound_speed_mps,
        "self_noise_frequency_hz": config.signal.self_noise_frequency_hz,
        "target_frequency_hz": config.signal.target_frequency_hz,
        "interference_bearing_deg": config.signal.interference_bearing_deg,
        "seed": config.seed,
    }
    with (output_dir / "generation_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(provenance, handle, indent=2)

    logger.info("Wrote dataset to %s  shape=%s", output_dir, data.shape)
    return output_dir
