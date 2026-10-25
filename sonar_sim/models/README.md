# DOA Classifier Models

This directory contains all five PyTorch classifier architectures used to estimate the
bearing angle of an acoustic source from the raw time-domain output of a 32-element
towed Uniform Linear Array (ULA).

---

## The Classification Task

Every sample entering a model is a **4096 × 32** float32 matrix — one second of
4096 Hz data across 32 hydrophones. The bearing θ ∈ {0°, 1°, …, 180°} is treated as
one of **181 classes**. The model outputs a 181-dimensional logit vector; the
predicted bearing is the argmax.

The operating condition is extreme: **SINR = −30 dB**. The target signal contributes
1/1000th the power of the self-noise interference. Classical beamformers fail
outright at this SNR, which is the whole motivation for the deep-learning approach.

---

## Input Layout

Generated data is stored as `(batch, time, sensors)` — i.e. `(B, 4096, 32)`.

Most models internally need `(batch, sensors, time)` — i.e. `(B, 32, 4096)` — so
that `Conv1d` treats each hydrophone channel as an independent input feature.
The helper `to_sensor_major` in `layout.py` handles the permutation:

```python
# sonar_sim/models/layout.py
def to_sensor_major(x: torch.Tensor, n_sensors: int = 32) -> torch.Tensor:
    """Return (batch, sensors, time) regardless of the incoming layout."""
    if x.dim() != 3:
        return x
    if x.size(1) == n_sensors:   # already (B, M, T)
        return x
    if x.size(2) == n_sensors:   # (B, T, M) → permute
        return x.permute(0, 2, 1).contiguous()
    return x
```

`MobileNet` is the exception — it receives pre-computed mel-spectrograms of shape
`(B, 32, 224, 224)` from `SpectrogramTransform` in `training/data.py`.

---

## Model Summary

| Key | Model | Input | Architecture | Params |
|---|---|---|---|---|
| `cnn_gru` | CNN-GRU | `(B, 32, 4096)` | Conv1D frontend → GRU blocks → attention pool | ~1–2 M |
| `bi_lstm` | Sinc-LSTM | `(B, 32, 4096)` | Sinc filterbank → 2-D CNN → LSTM → soft attention | ~3–4 M |
| `dracnn` | DRACNN | `(B, 32, 4096)` | Depthwise sensor frontend → 1-D CNN tower | ~1–2 M |
| `mlp` | MLP | `(B, 32, 4096)` | Log-FFT magnitude → NUMP pooling → MLP | ~0.4 M |
| `mobilenet` | MobileNet | `(B, 32, 224, 224)` | Init Conv2D → 6× depthwise-separable blocks | ~4–5 M |

Exact parameter counts depend on `d_model` / `n_layers` (CNN-GRU) and
`num_filters` / `lstm_hidden` (Sinc-LSTM). The table above uses the defaults from
`factory.py`.

---

## Architectures

### 1. CNN-GRU (`cnn_gru.py`) — Primary Model

The flagship architecture. A two-stage convolutional frontend compresses the 4096-sample
time axis before a stack of GRU blocks model the residual temporal structure. Soft
attention over the time dimension replaces mean pooling, preserving more of the
variance that encodes bearing.

**Why this design?**
- The Conv1D frontend acts as a learned filterbank, much cheaper than computing
  spectrograms explicitly.
- `InstanceNorm1d` normalises per-sample, per-channel — it is correct on the first
  batch where `BatchNorm1d`'s running statistics are not yet reliable.
- GRU with a residual LayerNorm projection (the `GRUBlock`) gives stable gradient flow
  at depth.
- `AttentionPool` is a single linear layer + softmax over the time axis — negligible
  cost, meaningful benefit.

```
Input  (B, 32, 4096)
  │
  ├── Conv1d(32→d, k=32, s=8)  InstanceNorm  GELU  Dropout(0.2)
  ├── Conv1d(d→d,  k=8,  s=2)  InstanceNorm  GELU
  │                                          shape: (B, d, ~256)
  │
  ├── GRUBlock × n_layers     (B, ~256, d)  →  (B, ~256, d)
  │   └── GRU(d→256) + Linear(256→d) + LayerNorm + GELU residual
  │
  ├── AttentionPool            (B, ~256, d) → (B, d)
  │
  └── Head: LayerNorm → Linear(d→256) → GELU → Dropout → Linear(256→181)
```

Default hyperparameters: `d_model=64`, `n_layers=1`. Override via `model_kwargs` in
`TrainConfig` or directly through `build_model`:

```python
from sonar_sim.models import build_model

model = build_model("cnn_gru", num_sensors=32, num_classes=181, d_model=128, n_layers=2)
```

---

### 2. Sinc-LSTM (`bi_lstm.py`)

`EndToEndSonarClassifier` is an end-to-end pipeline that avoids handcrafted STFT
features entirely. It initialises a grouped `Conv1d` as a **sinc filterbank** — the
weights are set analytically as windowed-sinc bandpass filters spanning 100–2000 Hz —
then learns to correct them during training.

The filterbank output is a `(B, M×F, T)` tensor that is reshaped into a 2-D
time-frequency representation, fed through three `Conv2d` blocks, then sequenced
through an LSTM with soft attention.

```
Input  (B, 32, 4096)
  │
  ├── Sinc filterbank   Conv1d(32→32×F, k=251, groups=32)  → (B, 32F, T)
  │   └── weights initialised as windowed-sinc bandpass filters
  ├── MaxPool1d(3)       log|·|
  │                                          shape: (B, 32F, T')
  │
  ├── Reshape → (B, 1, 32F, T')   [treat as 2-D image]
  ├── Conv2d(1→32)  BN  LeakyReLU  MaxPool2d  Dropout
  ├── Conv2d(32→64) BN  LeakyReLU  MaxPool2d  Dropout
  ├── Conv2d(64→128) BN LeakyReLU  MaxPool2d  Dropout
  ├── AdaptiveAvgPool2d(1, 64)     → (B, 128, 64)  permute → (B, 64, 128)
  │
  ├── LSTM(128→lstm_hidden, lstm_layers)
  ├── SoftAttention(lstm_hidden)   → (B, lstm_hidden)
  │
  └── Linear(lstm_hidden→64) → LeakyReLU → Dropout → Linear(64→181)
```

Default hyperparameters: `num_filters=64`, `kernel_size=251`, `lstm_layers=3`,
`lstm_hidden=128`.

---

### 3. DRACNN (`dracnn.py`)

`DOACNN` is a purely convolutional model built around **depthwise-separable 1-D
convolutions**. The sensor frontend is a grouped `Conv1d` that processes each
hydrophone independently (groups=M), expanding each channel by a factor of 4. This
learns per-sensor filters without mixing spatial information prematurely — the cross-sensor
mixing happens in the subsequent pointwise convolution stages.

The feature tower deepens from 64 → 128 → 256 channels with max-pooling and dropout
between blocks. An `AdaptiveAvgPool1d(1)` collapses the time axis at the end.

```
Input  (B, 32, 4096)
  │
  ├── Sensor frontend
  │   └── Conv1d(32→128, k=251, groups=32)  BN  ReLU   → (B, 128, 4096)
  │
  ├── Conv1d(128→64, k=7)  BN  ReLU
  ├── Conv1d(64→64,  k=7)  BN  ReLU  MaxPool1d(2)
  ├── Conv1d(64→128, k=5)  BN  ReLU
  ├── Conv1d(128→128, k=5) BN  ReLU  MaxPool1d(2)  Dropout(0.2)
  ├── Conv1d(128→256, k=5) BN  ReLU
  ├── Conv1d(256→256, k=5) BN  ReLU  AdaptiveAvgPool1d(1)
  │
  └── Flatten → Linear(256→128) → ReLU → Dropout(0.3) → Linear(128→181)
```

---

### 4. MLP (`mlp.py`)

`LightweightSonarMLP` is the computationally cheapest model. It converts the raw
time-domain input to its **log-magnitude FFT spectrum**, then applies a multi-scale
pooling module (`NUMP`) before the MLP head.

**NUMP** — Non-Uniform Multi-scale Pooling — divides the frequency axis into three
bands and applies progressively coarser max-pooling to each:

| Band | Frequency bins | Pool stride |
|---|---|---|
| Low | 0 – 256 | 2 |
| Mid | 256 – 512 | 8 |
| High | 512 – 2048 | 16 |

This mimics octave-spaced frequency resolution and produces a 256-dimensional feature
vector from a 2048-bin spectrum, regardless of input length.

```
Input  (B, 32, 4096)
  │
  ├── FFT(n=4096) → take first 2048 bins → log1p|·|  → (B, 32, 2048)
  ├── Reshape (B, 65536)   z-score normalise
  │
  ├── NUMP pooling         → (B, 256)  +  skip (B, 128)
  │
  ├── MLP: Linear(256→512) ReLU Dropout
  │        Linear(512→256) ReLU Dropout
  │        Linear(256→128) ReLU
  ├── LayerNorm(128)
  ├── Concat [skip(128), mlp_out(128)]  → (B, 256)
  │
  └── Linear(256→181)
```

The FFT is run once per forward pass on the GPU — fast, and the log-magnitude spectrum
is a well-conditioned feature for narrowband sources (BB0).

---

### 5. MobileNet (`mobilenet.py`)

`ModifiedMobileNet` is a 2-D convolutional model adapted from the MobileNet family.
It operates on **mel-spectrograms** rather than the raw time series. The data pipeline
(`SpectrogramTransform` in `training/data.py`) produces a `(B, 32, 224, 224)` tensor:
one 224×224 image per sensor channel, interpolated from the per-sensor STFT magnitude.

The network replaces the standard RGB input with a 32-channel input (one per sensor).
Six depthwise-separable `Conv2d` blocks with increasing channel depth (32 → 64 → 128
→ 256 → 512 → 512 → 1024) process the fused time-frequency-spatial representation.
The final three blocks use `Hardswish` instead of ReLU.

```
Input  (B, 32, 224, 224)
  │
  ├── Conv2d(32→32, k=3, s=2)  BN  Hardswish         → (B, 32, 112, 112)
  │
  ├── DepthwiseSep(32→64,   s=1, ReLU)               → (B, 64, 112, 112)
  ├── DepthwiseSep(64→128,  s=2, ReLU)               → (B, 128, 56, 56)
  ├── DepthwiseSep(128→256, s=2, ReLU)               → (B, 256, 28, 28)
  ├── DepthwiseSep(256→512, s=2, Hardswish)          → (B, 512, 14, 14)
  ├── DepthwiseSep(512→512, s=1, Hardswish)          → (B, 512, 14, 14)
  ├── DepthwiseSep(512→1024,s=2, Hardswish)          → (B, 1024, 7, 7)
  │
  ├── AdaptiveAvgPool2d(1, 1)  Flatten               → (B, 1024)
  └── Linear(1024→181)
```

Passing a raw time-series tensor `(B, 32, 4096)` raises a `ValueError`. The model
requires the spectrogram transform to be active, which is set automatically when
`model_name == "mobilenet"` in `TrainConfig`.

---

## Factory

All models are instantiated through `build_model` in `factory.py`:

```python
from sonar_sim.models import build_model

# defaults: num_sensors=32, num_classes=181
model = build_model("cnn_gru")
model = build_model("mlp")
model = build_model("bi_lstm")
model = build_model("dracnn")
model = build_model("mobilenet")

# override architecture hyperparameters
model = build_model("cnn_gru", d_model=128, n_layers=2)
model = build_model("bi_lstm", num_filters=32, lstm_layers=2, lstm_hidden=64)
```

The accepted keys:

| Model | Kwargs |
|---|---|
| `cnn_gru` | `d_model` (default 64), `n_layers` (default 1) |
| `bi_lstm` | `num_filters` (64), `kernel_size` (251), `lstm_layers` (3), `lstm_hidden` (128) |
| `dracnn` | — |
| `mlp` | — |
| `mobilenet` | — |

---

## Loss Function

All models are trained with `SoftCrossEntropyLoss` from `losses.py`:

```python
class SoftCrossEntropyLoss(nn.Module):
    def forward(self, logits, targets):
        log_probs = F.log_softmax(logits, dim=-1)
        return -(targets * log_probs).sum(dim=-1).mean()
```

This is standard cross-entropy extended to **soft (non-one-hot) targets**. The targets
come from `make_angular_smoothed_onehot` in `training/data.py`, which spreads a
fraction `smoothing` of the probability mass onto the `radius` nearest classes on each
side. With the defaults `smoothing=0.1, radius=1`, a 90° label becomes:

```
[..., 0.05, 0.90, 0.05, ...]   (neighbours each get 0.05)
```

This prevents overconfident predictions and correctly penalises predictions that are
off by 1° less than predictions off by 10°.

---

## Training Integration

### Single model

```bash
sonar-train --model cnn_gru --data-dir data/bb1_new --epochs 200
# or
python -m sonar_sim.training --model cnn_gru --data-dir data/bb1_new --epochs 200
```

### All models in one run

```bash
python -m sonar_sim.training.benchmark \
    --data-dir data/bb1_new \
    --models all \
    --results-dir results/comparison \
    --epochs 200
```

Output layout for each run:

```
results/
└── <model_name>/
    └── <YYYYMMDD_HHMMSS>/
        ├── models/
        │   └── best_model.pth        # checkpoint at best val loss
        └── json/
            ├── metrics.json          # accuracy, F1, precision, recall
            ├── config.json           # full TrainConfig snapshot
            ├── training_history.json # per-epoch loss and accuracy
            ├── confusion_matrix_data.json
            └── model_analysis.json   # params, FLOPs, latency, file size
```

### Optimizer and scheduler

All models use the same training setup (configured in `TrainConfig`):

| Setting | Default |
|---|---|
| Optimizer | Adam, lr=1e-3, weight_decay=1e-4 |
| Scheduler | ReduceLROnPlateau, patience=7, factor=0.5 |
| Early stopping | patience=25 epochs on val loss |
| Max epochs | 200 |
| Batch size | 16 (train/val), 256 (test) |
| Data split | 60 / 20 / 20 stratified by bearing |

### Endfire augmentation

Bearings 0°–30° and 150°–180° are physically harder to resolve (the cosine gradient
of the inter-sensor delay vanishes near endfire). During training, these samples are
replicated `copies=4` times in the training index, and a small Gaussian perturbation
(`noise_std=0.05`) is applied on-the-fly to those samples only.

---

## Plotting

After training, three plot modules consume the JSON outputs:

```bash
# Learning curves (loss + accuracy over epochs)
python -m sonar_sim.plots.learning_curves \
    --history results/comparison/cnn_gru/<stamp>/json/training_history.json \
    --out figures/cnn_gru_curves.png

# Grouped bar comparison across all models
python -m sonar_sim.plots.model_comparison \
    --results results/comparison/comparison_results.json \
    --out figures/model_comparison.png

# Confusion matrix, diagonal accuracy, per-bearing bars
python -m sonar_sim.plots.confusion_matrix \
    --cm results/comparison/cnn_gru/<stamp>/json/confusion_matrix_data.json \
    --out figures/cnn_gru_cm.png
```

The confusion matrix module plots three figures:
- **Full 181×181 heatmap** — row-normalised, ticks every 30°
- **Diagonal accuracy ribbon** — Acc±N° for N from 1° to 15°
- **Per-bearing accuracy bars** — endfire (0°–30°, 150°–180°) coloured separately

---

## Adding a New Model

1. Create `sonar_sim/models/my_model.py` and define a class that inherits
   `nn.Module`, accepts `num_sensors` and `num_classes` in `__init__`, and returns
   `(B, num_classes)` logits from `forward`.
2. Import it in `factory.py` and add a branch in `build_model`.
3. Add the name to `MODEL_NAMES` in `factory.py`.
4. Export the class from `__init__.py`.

The training pipeline, benchmark runner, and all plot utilities will pick up the new
model automatically once it is registered in the factory.
