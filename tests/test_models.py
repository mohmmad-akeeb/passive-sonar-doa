"""Tests for model architectures, factory, and plot utilities.

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
import torch.nn as nn

from sonar_sim.models.cnn_gru import AttentionPool, CNN_GRU, GRUBlock
from sonar_sim.models.dracnn import DOACNN
from sonar_sim.models.factory import MODEL_NAMES, build_model
from sonar_sim.models.losses import SoftCrossEntropyLoss
from sonar_sim.models.mlp import LightweightSonarMLP
from sonar_sim.plots.utils import model_color, model_label


# ===========================================================================
# GRUBlock
# ===========================================================================

class TestGRUBlock:
    def test_output_shape_preserved(self) -> None:
        block = GRUBlock(d_model=64, state_dim=128)
        x     = torch.randn(4, 32, 64)   # (B, T, d_model)
        out   = block(x)
        assert out.shape == x.shape

    def test_residual_connection_active(self) -> None:
        """Residual path: output for non-zero input must differ from all-zero output."""
        block  = GRUBlock(d_model=16, state_dim=16)
        x_real = torch.randn(2, 8, 16)
        x_zero = torch.zeros(2, 8, 16)
        with torch.no_grad():
            out_real = block(x_real)
            out_zero = block(x_zero)
        # A non-zero input must produce a different output than a zero input
        assert not torch.allclose(out_real, out_zero)

    def test_output_is_finite(self) -> None:
        block = GRUBlock(d_model=64, state_dim=128)
        x     = torch.randn(4, 50, 64)
        assert torch.all(torch.isfinite(block(x)))


# ===========================================================================
# AttentionPool
# ===========================================================================

class TestAttentionPool:
    def test_output_shape(self) -> None:
        pool = AttentionPool(d_model=128)
        x    = torch.randn(8, 64, 128)   # (B, T, d_model)
        out  = pool(x)
        assert out.shape == (8, 128)

    def test_weights_sum_to_one(self) -> None:
        """Attention weights over time dimension must sum to 1."""
        pool    = AttentionPool(d_model=32)
        x       = torch.randn(4, 20, 32)
        weights = torch.softmax(pool.attn(x), dim=1)   # (B, T, 1)
        assert torch.allclose(weights.sum(dim=1), torch.ones(4, 1), atol=1e-6)

    def test_output_is_finite(self) -> None:
        pool = AttentionPool(d_model=64)
        x    = torch.randn(4, 100, 64)
        assert torch.all(torch.isfinite(pool(x)))

    def test_single_time_step(self) -> None:
        pool = AttentionPool(d_model=32)
        x    = torch.randn(2, 1, 32)
        out  = pool(x)
        assert out.shape == (2, 32)


# ===========================================================================
# CNN_GRU
# ===========================================================================

class TestCNNGRU:
    def test_output_shape(self) -> None:
        model = CNN_GRU(num_sensors=32, d_model=64, n_layers=1, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(2, 4096, 32))
        assert out.shape == (2, 181)

    def test_logit_std_at_init_is_reasonable(self) -> None:
        """Logit std should be in [0.05, 3.0] at init — not collapsed or exploded."""
        torch.manual_seed(0)
        model = CNN_GRU(num_sensors=32, d_model=128, n_layers=2, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(16, 4096, 32))
        assert 0.05 < out.std().item() < 3.0, f"Logit std={out.std().item():.4f}"

    def test_different_inputs_give_different_outputs(self) -> None:
        model = CNN_GRU(num_sensors=32, d_model=64, n_layers=1, num_classes=181)
        model.eval()
        with torch.no_grad():
            out1 = model(torch.randn(2, 4096, 32))
            out2 = model(torch.randn(2, 4096, 32))
        assert not torch.allclose(out1, out2)

    def test_output_is_finite(self) -> None:
        model = CNN_GRU()
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(4, 4096, 32))
        assert torch.all(torch.isfinite(out))

    def test_custom_d_model_and_layers(self) -> None:
        model = CNN_GRU(num_sensors=32, d_model=256, n_layers=3, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(2, 4096, 32))
        assert out.shape == (2, 181)

    def test_gradient_flows_to_all_parameters(self) -> None:
        model = CNN_GRU(num_sensors=32, d_model=64, n_layers=1, num_classes=181)
        x = torch.randn(2, 4096, 32)
        y = torch.zeros(2, 181); y[0, 90] = 1.0; y[1, 45] = 1.0
        loss = SoftCrossEntropyLoss()(model(x), y)
        loss.backward()
        dead = [n for n, p in model.named_parameters()
                if p.requires_grad and p.grad is None]
        assert dead == [], f"No gradient for: {dead}"

    def test_instance_norm_not_batch_norm(self) -> None:
        """Confirm BatchNorm1d was replaced — model must work with batch_size=1."""
        model = CNN_GRU(num_sensors=32, d_model=64, n_layers=1, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(1, 4096, 32))   # batch of 1 — crashes BatchNorm
        assert out.shape == (1, 181)

    @pytest.mark.parametrize("batch", [1, 4, 16])
    def test_variable_batch_sizes(self, batch: int) -> None:
        model = CNN_GRU(num_sensors=32, d_model=64, n_layers=1, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(batch, 4096, 32))
        assert out.shape == (batch, 181)


# ===========================================================================
# DOACNN (DRACNN)
# ===========================================================================

class TestDOACNN:
    def test_output_shape(self) -> None:
        model = DOACNN(num_sensors=32, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(2, 4096, 32))
        assert out.shape == (2, 181)

    def test_output_finite(self) -> None:
        model = DOACNN()
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(2, 4096, 32))
        assert torch.all(torch.isfinite(out))


# ===========================================================================
# LightweightSonarMLP
# ===========================================================================

class TestMLP:
    def test_output_shape(self) -> None:
        model = LightweightSonarMLP(num_sensors=32, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(2, 4096, 32))
        assert out.shape == (2, 181)

    def test_output_finite(self) -> None:
        model = LightweightSonarMLP()
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(4, 4096, 32))
        assert torch.all(torch.isfinite(out))


# ===========================================================================
# build_model factory
# ===========================================================================

class TestBuildModel:
    @pytest.mark.parametrize("name", list(MODEL_NAMES))
    def test_all_model_names_instantiate(self, name: str) -> None:
        model = build_model(name, num_sensors=32, num_classes=181)
        assert isinstance(model, nn.Module)

    def test_raises_on_unknown_name(self) -> None:
        with pytest.raises(ValueError, match="Unknown model"):
            build_model("not_a_model")

    def test_cnn_gru_kwargs_d_model(self) -> None:
        model = build_model("cnn_gru", d_model=256)
        # Verify d_model propagated — check feature extractor out_channels
        conv = model.feature_extractor[0]
        assert conv.out_channels == 256

    def test_cnn_gru_kwargs_n_layers(self) -> None:
        model = build_model("cnn_gru", n_layers=3)
        assert len(model.ssm_layers) == 3

    def test_model_names_tuple_is_complete(self) -> None:
        """MODEL_NAMES must match the set of keys build_model handles."""
        for name in MODEL_NAMES:
            build_model(name)   # must not raise

    @pytest.mark.parametrize("name", ["cnn_gru", "mlp", "bi_lstm", "dracnn"])
    def test_forward_pass_shape_contract(self, name: str) -> None:
        """(B, T, M) → (B, 181) for all time-domain models."""
        model = build_model(name, num_sensors=32, num_classes=181)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(2, 4096, 32))
        assert out.shape == (2, 181)

    @pytest.mark.parametrize("name", ["cnn_gru", "mlp", "bi_lstm", "dracnn"])
    def test_forward_pass_finite(self, name: str) -> None:
        model = build_model(name)
        model.eval()
        with torch.no_grad():
            out = model(torch.randn(2, 4096, 32))
        assert torch.all(torch.isfinite(out)), f"{name}: non-finite output"


# ===========================================================================
# plots/utils — colour palette and label helpers
# ===========================================================================

class TestPlotUtils:
    @pytest.mark.parametrize("name,expected", [
        ("cnn_gru",   "#0072B2"),
        ("bi_lstm",   "#E69F00"),
        ("dracnn",    "#009E73"),
        ("mlp",       "#D55E00"),
        ("mobilenet", "#CC79A7"),
    ])
    def test_model_color_known_names(self, name: str, expected: str) -> None:
        assert model_color(name) == expected

    def test_model_color_unknown_name_fallback(self) -> None:
        color = model_color("unknown_model", idx=0)
        assert color.startswith("#")
        assert len(color) == 7

    @pytest.mark.parametrize("name,expected", [
        ("cnn_gru",   "CNN-GRU"),
        ("bi_lstm",   "Bi-LSTM"),
        ("dracnn",    "DRACNN"),
        ("mlp",       "MLP"),
        ("mobilenet", "MobileNet"),
    ])
    def test_model_label_known_names(self, name: str, expected: str) -> None:
        assert model_label(name) == expected

    def test_model_label_unknown_name_passthrough(self) -> None:
        assert model_label("my_custom_model") == "my_custom_model"

    def test_model_color_case_insensitive(self) -> None:
        assert model_color("CNN_GRU") == model_color("cnn_gru")

    def test_model_label_dash_alias(self) -> None:
        """'cnn-gru' should resolve same as 'cnn_gru'."""
        assert model_label("cnn-gru") == model_label("cnn_gru")
