"""Tests for the training pipeline: loss, label smoothing, data loading, transforms.

Run from repo root:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

from sonar_sim.models.losses import SoftCrossEntropyLoss
from sonar_sim.training.config import TrainConfig
from sonar_sim.training.data import (
    SonarDataset,
    TimeDomainTransform,
    augment_endfire_train_indices,
    build_loaders,
    make_angular_smoothed_onehot,
    stratified_split,
)


# ===========================================================================
# SoftCrossEntropyLoss
# ===========================================================================

class TestSoftCrossEntropyLoss:
    def test_matches_manual_formula(self) -> None:
        """Loss == -sum(p * log_softmax(logits)) mean over batch."""
        torch.manual_seed(0)
        logits  = torch.randn(8, 181)
        targets = torch.zeros(8, 181)
        targets[torch.arange(8), torch.randint(0, 181, (8,))] = 1.0

        criterion = SoftCrossEntropyLoss()
        computed  = criterion(logits, targets)

        log_probs = torch.log_softmax(logits, dim=-1)
        expected  = -(targets * log_probs).sum(dim=-1).mean()
        assert torch.isclose(computed, expected, atol=1e-6)

    def test_one_hot_target_equals_standard_cross_entropy(self) -> None:
        torch.manual_seed(1)
        logits  = torch.randn(16, 10)
        labels  = torch.randint(0, 10, (16,))
        targets = torch.zeros(16, 10)
        targets[torch.arange(16), labels] = 1.0

        soft_ce   = SoftCrossEntropyLoss()(logits, targets)
        hard_ce   = torch.nn.CrossEntropyLoss()(logits, labels)
        assert torch.isclose(soft_ce, hard_ce, atol=1e-5)

    def test_uniform_target_gives_log_num_classes(self) -> None:
        """If targets are uniform, loss = log(num_classes)."""
        n_classes = 181
        logits    = torch.zeros(4, n_classes)
        targets   = torch.full((4, n_classes), 1.0 / n_classes)
        loss      = SoftCrossEntropyLoss()(logits, targets)
        assert loss.item() == pytest.approx(np.log(n_classes), rel=1e-4)

    def test_loss_decreases_with_gradient_step(self) -> None:
        torch.manual_seed(2)
        model = torch.nn.Linear(64, 181)
        opt   = torch.optim.Adam(model.parameters(), lr=1e-2)
        x     = torch.randn(16, 64)
        y     = torch.zeros(16, 181)
        y[torch.arange(16), torch.randint(0, 181, (16,))] = 1.0

        criterion = SoftCrossEntropyLoss()
        losses = []
        for _ in range(20):
            opt.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            opt.step()
            losses.append(loss.item())
        assert losses[-1] < losses[0], "Loss did not decrease"

    def test_output_is_scalar(self) -> None:
        logits  = torch.randn(4, 181)
        targets = torch.softmax(torch.randn(4, 181), dim=-1)
        loss    = SoftCrossEntropyLoss()(logits, targets)
        assert loss.shape == torch.Size([])

    def test_gradient_flows_through_logits(self) -> None:
        logits  = torch.randn(4, 181, requires_grad=True)
        targets = torch.softmax(torch.randn(4, 181), dim=-1)
        loss    = SoftCrossEntropyLoss()(logits, targets)
        loss.backward()
        assert logits.grad is not None
        assert logits.grad.shape == logits.shape
        assert torch.all(torch.isfinite(logits.grad))


# ===========================================================================
# make_angular_smoothed_onehot
# ===========================================================================

class TestAngularSmoothing:
    def test_hard_labels_when_smoothing_zero(self) -> None:
        labels = torch.tensor([0, 90, 180])
        y = make_angular_smoothed_onehot(labels, 181, smoothing=0.0, radius=1)
        assert y.shape == (3, 181)
        assert y[0, 0]   == pytest.approx(1.0)
        assert y[1, 90]  == pytest.approx(1.0)
        assert y[2, 180] == pytest.approx(1.0)

    def test_rows_sum_to_one(self) -> None:
        labels = torch.tensor([0, 45, 90, 135, 180])
        y = make_angular_smoothed_onehot(labels, 181, smoothing=0.1, radius=2)
        assert torch.allclose(y.sum(dim=1), torch.ones(5), atol=1e-6)

    def test_centre_class_has_most_mass(self) -> None:
        labels = torch.tensor([90])
        y = make_angular_smoothed_onehot(labels, 181, smoothing=0.1, radius=3)
        assert y[0, 90] > y[0, 89]
        assert y[0, 90] > y[0, 91]

    def test_neighbours_get_nonzero_mass(self) -> None:
        labels = torch.tensor([90])
        y = make_angular_smoothed_onehot(labels, 181, smoothing=0.1, radius=1)
        assert y[0, 89] > 0.0
        assert y[0, 91] > 0.0

    def test_edge_class_zero_does_not_crash(self) -> None:
        labels = torch.tensor([0])
        y = make_angular_smoothed_onehot(labels, 181, smoothing=0.1, radius=2)
        assert y.shape == (1, 181)
        assert torch.allclose(y.sum(dim=1), torch.ones(1), atol=1e-6)

    def test_edge_class_180_does_not_crash(self) -> None:
        labels = torch.tensor([180])
        y = make_angular_smoothed_onehot(labels, 181, smoothing=0.1, radius=2)
        assert y.shape == (1, 181)
        assert torch.allclose(y.sum(dim=1), torch.ones(1), atol=1e-6)

    def test_output_is_non_negative(self) -> None:
        labels = torch.arange(0, 181, 10)
        y = make_angular_smoothed_onehot(labels, 181, smoothing=0.2, radius=3)
        assert torch.all(y >= 0.0)

    def test_larger_radius_spreads_mass_further(self) -> None:
        labels = torch.tensor([90])
        y_r1 = make_angular_smoothed_onehot(labels, 181, smoothing=0.1, radius=1)
        y_r5 = make_angular_smoothed_onehot(labels, 181, smoothing=0.1, radius=5)
        # r=1: only 89,90,91 are nonzero; r=5: 85–95 are nonzero
        assert y_r1[0, 85] == pytest.approx(0.0)
        assert y_r5[0, 85] > 0.0


# ===========================================================================
# stratified_split
# ===========================================================================

class TestStratifiedSplit:
    def _make_labels(self, n_classes: int = 181, repeats: int = 10) -> np.ndarray:
        return np.tile(np.arange(n_classes), repeats)

    def test_split_sizes_sum_to_total(self) -> None:
        labels = self._make_labels()
        idx = np.arange(len(labels))
        tr, val, te = stratified_split(idx, labels, 0.6, 0.2, 0.2, seed=0)
        assert len(tr) + len(val) + len(te) == len(labels)

    def test_split_ratios_approximate(self) -> None:
        labels = self._make_labels()
        idx = np.arange(len(labels))
        tr, val, te = stratified_split(idx, labels, 0.6, 0.2, 0.2, seed=0)
        n = len(labels)
        assert abs(len(tr) / n - 0.6) < 0.05
        assert abs(len(val) / n - 0.2) < 0.05
        assert abs(len(te) / n - 0.2) < 0.05

    def test_splits_are_disjoint(self) -> None:
        labels = self._make_labels()
        idx = np.arange(len(labels))
        tr, val, te = stratified_split(idx, labels, 0.6, 0.2, 0.2, seed=0)
        assert len(set(tr) & set(val)) == 0
        assert len(set(tr) & set(te)) == 0
        assert len(set(val) & set(te)) == 0

    def test_reproducible_with_same_seed(self) -> None:
        labels = self._make_labels()
        idx = np.arange(len(labels))
        tr1, _, _ = stratified_split(idx, labels, 0.6, 0.2, 0.2, seed=42)
        tr2, _, _ = stratified_split(idx, labels, 0.6, 0.2, 0.2, seed=42)
        assert np.array_equal(tr1, tr2)

    def test_different_seeds_give_different_splits(self) -> None:
        labels = self._make_labels()
        idx = np.arange(len(labels))
        tr1, _, _ = stratified_split(idx, labels, 0.6, 0.2, 0.2, seed=0)
        tr2, _, _ = stratified_split(idx, labels, 0.6, 0.2, 0.2, seed=1)
        assert not np.array_equal(tr1, tr2)


# ===========================================================================
# augment_endfire_train_indices
# ===========================================================================

class TestEndfireAugmentation:
    def test_augmented_set_is_larger(self) -> None:
        labels = np.tile(np.arange(181), 5)
        idx    = np.arange(len(labels))
        aug    = augment_endfire_train_indices(idx, labels, ((0, 30), (150, 180)), copies=4)
        assert len(aug) > len(idx)

    def test_endfire_indices_appear_more_often(self) -> None:
        labels  = np.tile(np.arange(181), 5)
        idx     = np.arange(len(labels))
        aug     = augment_endfire_train_indices(idx, labels, ((0, 30), (150, 180)), copies=4)
        aug_labels = labels[aug]
        broadside_count = np.sum((aug_labels > 30) & (aug_labels < 150))
        endfire_count   = np.sum((aug_labels <= 30) | (aug_labels >= 150))
        # endfire should represent more than their 1/3 natural share after 4 copies
        assert endfire_count > broadside_count * 0.5

    def test_zero_copies_returns_original(self) -> None:
        labels = np.tile(np.arange(181), 5)
        idx    = np.arange(len(labels))
        aug    = augment_endfire_train_indices(idx, labels, ((0, 30), (150, 180)), copies=0)
        assert len(aug) == len(idx)


# ===========================================================================
# TrainConfig
# ===========================================================================

class TestTrainConfig:
    def test_defaults_are_sane(self) -> None:
        cfg = TrainConfig()
        assert cfg.num_classes == 181
        assert cfg.num_sensors == 32
        assert 0 < cfg.train_ratio < 1
        assert cfg.train_ratio + cfg.val_ratio + cfg.test_ratio == pytest.approx(1.0)

    def test_to_json_dict_is_serialisable(self) -> None:
        cfg = TrainConfig()
        d   = cfg.to_json_dict()
        # must round-trip through json without error
        s = json.dumps(d)
        assert isinstance(json.loads(s), dict)

    def test_to_json_dict_paths_are_strings(self) -> None:
        cfg = TrainConfig(data_dir=Path("data/bb1_new"))
        d   = cfg.to_json_dict()
        assert isinstance(d["data_dir"], str)
        assert isinstance(d["results_dir"], str)

    def test_endfire_ranges_serialised_as_lists(self) -> None:
        cfg = TrainConfig()
        d   = cfg.to_json_dict()
        for pair in d["endfire_ranges"]:
            assert isinstance(pair, list)


# ===========================================================================
# TimeDomainTransform
# ===========================================================================

class TestTimeDomainTransform:
    def _make_transform(self, **kwargs) -> TimeDomainTransform:
        return TimeDomainTransform(TrainConfig(**kwargs))

    def test_output_x_shape_unchanged(self) -> None:
        t = self._make_transform()
        x = torch.randn(4096, 32)
        y = torch.tensor(90)
        x_out, y_out = t(x, y, is_train=False)
        assert x_out.shape == (4096, 32)

    def test_output_y_is_soft_distribution(self) -> None:
        t = self._make_transform()
        x = torch.randn(4096, 32)
        _, y_out = t(torch.randn(4096, 32), torch.tensor(90), is_train=False)
        assert y_out.shape == (181,)
        assert y_out.sum().item() == pytest.approx(1.0, abs=1e-5)
        assert torch.all(y_out >= 0)

    def test_normalisation_gives_zero_mean_unit_std(self) -> None:
        t = self._make_transform()
        x = torch.randn(4096, 32) * 100 + 50   # deliberately un-normalised
        x_out, _ = t(x, torch.tensor(45), is_train=False)
        assert x_out.mean(dim=0).abs().max().item() < 1e-5
        assert x_out.std(dim=0).mean().item() == pytest.approx(1.0, abs=1e-4)

    def test_train_noise_augmentation_changes_x(self) -> None:
        """Endfire samples should be perturbed during training."""
        t   = self._make_transform(noise_std=0.5)
        x   = torch.zeros(4096, 32)
        x1, _ = t(x.clone(), torch.tensor(10), is_train=True)   # endfire
        x2, _ = t(x.clone(), torch.tensor(10), is_train=True)
        # Two augmented outputs should differ (stochastic noise)
        assert not torch.allclose(x1, x2)

    def test_inference_no_augmentation(self) -> None:
        """Same input → same output at inference."""
        t  = self._make_transform(noise_std=0.5)
        x  = torch.randn(4096, 32)
        x1, _ = t(x.clone(), torch.tensor(10), is_train=False)
        x2, _ = t(x.clone(), torch.tensor(10), is_train=False)
        assert torch.allclose(x1, x2)


# ===========================================================================
# SonarDataset + build_loaders (uses a tiny synthetic .npy fixture)
# ===========================================================================

@pytest.fixture(scope="module")
def tiny_data_dir(tmp_path_factory):
    """Write a (60, 4096, 32) noisy.npy + labels.npy to a temp dir.

    10 bearings × 6 repeats = 60 samples.
    Stratified split needs ≥ 2 samples per class and test_size ≥ n_classes (10).
    With 60 samples: train=36, val=12, test=12 — all constraints satisfied.
    """
    tmp = tmp_path_factory.mktemp("data")
    rng = np.random.default_rng(0)
    n_bearings = 10
    repeats    = 6
    n          = n_bearings * repeats
    bearings   = np.tile(np.arange(0, 181, 20), repeats)   # 0,20,...,180 × 6
    data       = rng.standard_normal((n, 4096, 32)).astype(np.float32)
    np.save(tmp / "noisy.npy",  data)
    np.save(tmp / "labels.npy", bearings.astype(np.int16))
    return tmp


class TestSonarDataset:
    def test_len(self, tiny_data_dir) -> None:
        labels = np.load(tiny_data_dir / "labels.npy").flatten()
        idx    = np.arange(len(labels))
        cfg    = TrainConfig(data_dir=tiny_data_dir)
        t      = TimeDomainTransform(cfg)
        ds     = SonarDataset(tiny_data_dir / "noisy.npy", idx, labels, t, False)
        assert len(ds) == len(labels)

    def test_getitem_shapes(self, tiny_data_dir) -> None:
        labels = np.load(tiny_data_dir / "labels.npy").flatten()
        idx    = np.arange(len(labels))
        cfg    = TrainConfig(data_dir=tiny_data_dir)
        t      = TimeDomainTransform(cfg)
        ds     = SonarDataset(tiny_data_dir / "noisy.npy", idx, labels, t, False)
        x, y   = ds[0]
        assert x.shape == (4096, 32)
        assert y.shape == (181,)

    def test_getitem_x_is_finite(self, tiny_data_dir) -> None:
        labels = np.load(tiny_data_dir / "labels.npy").flatten()
        idx    = np.arange(len(labels))
        cfg    = TrainConfig(data_dir=tiny_data_dir)
        t      = TimeDomainTransform(cfg)
        ds     = SonarDataset(tiny_data_dir / "noisy.npy", idx, labels, t, False)
        x, _   = ds[0]
        assert torch.all(torch.isfinite(x))

    def test_getitem_y_sums_to_one(self, tiny_data_dir) -> None:
        labels = np.load(tiny_data_dir / "labels.npy").flatten()
        idx    = np.arange(len(labels))
        cfg    = TrainConfig(data_dir=tiny_data_dir)
        t      = TimeDomainTransform(cfg)
        ds     = SonarDataset(tiny_data_dir / "noisy.npy", idx, labels, t, False)
        for i in range(min(5, len(ds))):
            _, y = ds[i]
            assert y.sum().item() == pytest.approx(1.0, abs=1e-5)


class TestBuildLoaders:
    def test_returns_three_loaders(self, tiny_data_dir) -> None:
        cfg = TrainConfig(
            data_dir=tiny_data_dir, num_workers=0,
            batch_size_train=4, batch_size_val=4, batch_size_test=4,
            copies=0,   # no endfire augmentation on tiny data
        )
        loaders = build_loaders(cfg)
        assert len(loaders) == 3

    def test_loader_batch_shapes(self, tiny_data_dir) -> None:
        cfg = TrainConfig(
            data_dir=tiny_data_dir, num_workers=0,
            batch_size_train=4, batch_size_val=4, batch_size_test=4,
            copies=0,
        )
        train_loader, val_loader, test_loader = build_loaders(cfg)
        for loader in (train_loader, val_loader, test_loader):
            batch_x, batch_y = next(iter(loader))
            assert batch_x.ndim == 3                    # (B, T, M)
            assert batch_x.shape[1] == 4096
            assert batch_x.shape[2] == 32
            assert batch_y.ndim == 2                    # (B, num_classes)
            assert batch_y.shape[1] == 181

    def test_loader_x_dtype_is_float32(self, tiny_data_dir) -> None:
        cfg = TrainConfig(
            data_dir=tiny_data_dir, num_workers=0,
            batch_size_train=4, copies=0,
        )
        train_loader, _, _ = build_loaders(cfg)
        batch_x, _ = next(iter(train_loader))
        assert batch_x.dtype == torch.float32

    def test_loader_y_sums_to_one(self, tiny_data_dir) -> None:
        cfg = TrainConfig(
            data_dir=tiny_data_dir, num_workers=0,
            batch_size_val=4, copies=0,
        )
        _, val_loader, _ = build_loaders(cfg)
        _, batch_y = next(iter(val_loader))
        assert torch.allclose(batch_y.sum(dim=1), torch.ones(batch_y.shape[0]), atol=1e-5)

    def test_splits_are_disjoint(self, tiny_data_dir) -> None:
        """No sample index should appear in more than one split."""
        cfg = TrainConfig(
            data_dir=tiny_data_dir, num_workers=0,
            batch_size_train=20, batch_size_val=20, batch_size_test=20,
            copies=0,
        )
        train_loader, val_loader, test_loader = build_loaders(cfg)
        # Collect all indices via the underlying dataset
        tr_idx  = set(train_loader.dataset.indices.tolist())
        val_idx = set(val_loader.dataset.indices.tolist())
        te_idx  = set(test_loader.dataset.indices.tolist())
        assert len(tr_idx & val_idx) == 0
        assert len(tr_idx & te_idx)  == 0
        assert len(val_idx & te_idx) == 0
