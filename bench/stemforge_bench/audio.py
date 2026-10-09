"""Small audio helpers shared by adapters and datasets (numpy/scipy/soundfile only)."""
from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def resample(audio: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    """Polyphase resample along the last axis. Returns float32."""
    if sr_from == sr_to:
        return audio.astype(np.float32, copy=False)
    g = gcd(sr_from, sr_to)
    return resample_poly(audio, sr_to // g, sr_from // g, axis=-1).astype(np.float32)


def fit_length(audio: np.ndarray, n: int) -> np.ndarray:
    if audio.shape[-1] >= n:
        return audio[..., :n]
    pad = [(0, 0)] * (audio.ndim - 1) + [(0, n - audio.shape[-1])]
    return np.pad(audio, pad)


def to_stereo(audio: np.ndarray) -> np.ndarray:
    return np.repeat(audio, 2, axis=0) if audio.shape[0] == 1 else audio


def from_stereo(stereo: np.ndarray, channels: int) -> np.ndarray:
    return stereo.mean(axis=0, keepdims=True) if channels == 1 else stereo


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data.T.copy(), sr


def write_audio(path: Path, audio: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio.T, sr, subtype="PCM_16")
