"""Memory-mapped snapshot loading, splits, and label smoothing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset

from sonar_sim.models.layout import to_sensor_major
from sonar_sim.training.config import TrainConfig


def load_labels(path: Path) -> np.ndarray:
    if path.suffix == ".npy":
        return np.load(path).astype(int).flatten()
    import h5py

    try:
        with h5py.File(path, "r") as handle:
            key = "TBAll" if "TBAll" in handle else next(iter(handle.keys()))
            return np.array(handle[key]).astype(int).flatten()
    except OSError:
        from scipy.io import loadmat

        mat = loadmat(path)
        key = "TBAll" if "TBAll" in mat else next(k for k in mat if not k.startswith("_"))
        return np.asarray(mat[key]).astype(int).flatten()


def make_angular_smoothed_onehot(
    labels_int: torch.Tensor,
    num_classes: int,
    smoothing: float,
    radius: int = 1,
) -> torch.Tensor:
    n = labels_int.shape[0]
    y = torch.zeros((n, num_classes), dtype=torch.float32)
    if radius < 1 or smoothing == 0.0:
        y[torch.arange(n), labels_int] = 1.0
        return y
    main_mass = 1.0 - smoothing
    share = smoothing / (2 * radius)
    for i, cls in enumerate(labels_int.tolist()):
        y[i, cls] = main_mass
        for offset in range(1, radius + 1):
            y[i, (cls - offset) % num_classes] += share
            y[i, (cls + offset) % num_classes] += share
    return y


def stratified_split(
    indices: np.ndarray,
    labels: np.ndarray,
    train: float,
    val: float,
    test: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    idx_tr, idx_tmp, _, y_tmp = train_test_split(
        indices, labels, test_size=(1 - train), stratify=labels, random_state=seed
    )
    idx_val, idx_test, _, _ = train_test_split(
        idx_tmp,
        y_tmp,
        test_size=test / (val + test),
        stratify=y_tmp,
        random_state=seed,
    )
    return idx_tr, idx_val, idx_test


def augment_endfire_train_indices(
    train_indices: np.ndarray,
    all_labels: np.ndarray,
    endfire_ranges: tuple[tuple[int, int], ...],
    copies: int,
) -> np.ndarray:
    train_labels = all_labels[train_indices]
    mask = np.zeros_like(train_labels, dtype=bool)
    for low, high in endfire_ranges:
        mask |= (train_labels >= low) & (train_labels <= high)
    extra = [train_indices] + [train_indices[mask]] * copies
    final = np.concatenate(extra)
    np.random.shuffle(final)
    return final


class SonarDataset(Dataset):
    def __init__(
        self,
        data_path: Path,
        indices: np.ndarray,
        labels: np.ndarray,
        transform,
        is_train: bool,
    ) -> None:
        self.data_path = data_path
        self.indices = np.asarray(indices)
        self.labels = np.asarray(labels)
        self.transform = transform
        self.is_train = is_train
        self._mmap = np.load(data_path, mmap_mode="r")

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int):
        real_idx = int(self.indices[idx])
        x = torch.from_numpy(np.array(self._mmap[real_idx], copy=True)).float()
        y = torch.tensor(int(self.labels[real_idx]), dtype=torch.long)
        return self.transform(x, y, self.is_train)


class TimeDomainTransform:
    def __init__(self, config: TrainConfig) -> None:
        self.config = config

    def __call__(self, x: torch.Tensor, y: torch.Tensor, is_train: bool):
        angle = int(y.item())
        if is_train and any(lo <= angle <= hi for lo, hi in self.config.endfire_ranges):
            x = x + torch.randn_like(x) * self.config.noise_std
        if x.dim() == 2:
            mean = x.mean(dim=0, keepdim=True)
            std = x.std(dim=0, keepdim=True) + 1e-8
            x = (x - mean) / std
        y_soft = make_angular_smoothed_onehot(
            torch.tensor([angle]),
            self.config.num_classes,
            self.config.smoothing,
            self.config.radius,
        )[0]
        return x, y_soft


class SpectrogramTransform(TimeDomainTransform):
    def __init__(self, config: TrainConfig) -> None:
        super().__init__(config)
        self.fir_kernel = torch.ones(1, 1, 5) / 5.0
        self.n_fft = 256
        self.hop_length = 64

    def __call__(self, x: torch.Tensor, y: torch.Tensor, is_train: bool):
        x, y_soft = TimeDomainTransform.__call__(self, x, y, is_train)
        x = to_sensor_major(x.unsqueeze(0), self.config.num_sensors).squeeze(0)
        x = F.conv1d(x.unsqueeze(1), self.fir_kernel, padding=2).squeeze(1)
        x = x[:, ::2]
        window = torch.hamming_window(self.n_fft)
        stft = torch.stft(
            x,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window=window,
            return_complex=True,
        )
        mag = stft.abs().unsqueeze(0)
        mag = F.interpolate(mag, size=(224, 224), mode="bilinear", align_corners=False).squeeze(0)
        mean = mag.mean(dim=(1, 2), keepdim=True)
        std = mag.std(dim=(1, 2), keepdim=True) + 1e-8
        return (mag - mean) / std, y_soft


def build_loaders(config: TrainConfig) -> tuple[DataLoader, DataLoader, DataLoader]:
    data_root = Path(config.data_dir)
    labels = load_labels(data_root / config.labels_file)
    signal_path = data_root / config.signal_file
    indices = np.arange(len(labels))
    idx_tr, idx_val, idx_test = stratified_split(
        indices,
        labels,
        config.train_ratio,
        config.val_ratio,
        config.test_ratio,
        config.seed,
    )
    idx_tr = augment_endfire_train_indices(
        idx_tr, labels, config.endfire_ranges, config.copies
    )
    transform = (
        SpectrogramTransform(config)
        if config.model_name.lower() == "mobilenet"
        else TimeDomainTransform(config)
    )
    loaders = []
    for split_idx, is_train, batch in (
        (idx_tr, True, config.batch_size_train),
        (idx_val, False, config.batch_size_val),
        (idx_test, False, config.batch_size_test),
    ):
        dataset = SonarDataset(signal_path, split_idx, labels, transform, is_train)
        loaders.append(
            DataLoader(
                dataset,
                batch_size=batch,
                shuffle=is_train,
                num_workers=config.num_workers,
                pin_memory=True,
            )
        )
    return loaders[0], loaders[1], loaders[2]
