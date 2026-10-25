"""Command-line entry point: ``python -m sonar_sim.generation``."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np

from sonar_sim.generation.config import SimulationConfig
from sonar_sim.generation.dataset import DatasetSpec, generate_dataset, save_dataset


def _parse_bearings(spec: str) -> np.ndarray:
    """Parse ``start:stop:step`` (inclusive stop) or a comma-separated list."""
    if "," in spec:
        return np.array([float(part) for part in spec.split(",")], dtype=np.float64)
    start_s, stop_s, *rest = spec.split(":")
    step = float(rest[0]) if rest else 1.0
    start, stop = float(start_s), float(stop_s)
    return np.arange(start, stop + 0.5 * step, step)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate synthetic passive-SONAR ULA snapshots (thesis physics)."
    )
    parser.add_argument("--bb", type=int, choices=(0, 1), default=0, help="0=narrowband, 1=wideband")
    parser.add_argument("--sinr", type=float, default=-30.0, help="Target SINR in dB")
    parser.add_argument("--interference-snr", type=float, default=20.0)
    parser.add_argument("--duration", type=int, default=1, help="Seconds per snapshot")
    parser.add_argument("--bearings", type=str, default="0:180:1", help="start:stop:step or a,b,c")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("data"))
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    config = SimulationConfig(
        broadband=bool(args.bb),
        sinr_db=args.sinr,
        interference_snr_db=args.interference_snr,
        duration_s=args.duration,
        seed=args.seed,
    )
    spec = DatasetSpec(
        bearings_deg=_parse_bearings(args.bearings),
        repeats=args.repeats,
        output_dir=args.out_dir,
    )
    data, labels = generate_dataset(config, spec)
    save_dataset(data, labels, config, args.out_dir)


if __name__ == "__main__":
    main()
