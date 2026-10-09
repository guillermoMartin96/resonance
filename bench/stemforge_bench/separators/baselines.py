"""Non-ML reference points.

- MixtureBaseline: every stem estimate is the unmodified mixture. This is the
  standard "do nothing" floor for SDR and the pass-through used to test the
  playback pipeline without any model installed.
- HPSSBaseline: classical harmonic/percussive separation by median filtering
  (Fitzgerald 2010) plus a low-pass split of the harmonic part for bass. Shows
  what can be had with zero model weights and zero licensing questions.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import istft, stft

from .base import SeparatorInfo, validate_input


class MixtureBaseline:
    def __init__(self) -> None:
        self.info = SeparatorInfo(
            id="baseline.mixture", engine="baseline", engine_version="1",
            model_name="identity", native_sample_rate=0,
            roles=("vocals", "drums", "bass", "other", "accompaniment"),
            code_license="project", weights_license="n/a (no weights)",
        )

    def load(self) -> None:
        pass

    def separate(self, audio: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        audio = validate_input(audio, sample_rate)
        return {role: audio.copy() for role in self.info.roles}


class HPSSBaseline:
    def __init__(self, n_fft: int = 4096, kernel: int = 17, bass_cutoff_hz: float = 180.0) -> None:
        self.n_fft, self.kernel, self.bass_cutoff_hz = n_fft, kernel, bass_cutoff_hz
        self.info = SeparatorInfo(
            id="baseline.hpss", engine="baseline", engine_version="1",
            model_name="median-filter-hpss", native_sample_rate=0,
            roles=("drums", "bass", "other"),
            code_license="project", weights_license="n/a (no weights)",
            params={"n_fft": n_fft, "kernel": kernel, "bass_cutoff_hz": bass_cutoff_hz},
        )

    def load(self) -> None:
        pass

    def separate(self, audio: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        audio = validate_input(audio, sample_rate)
        n = audio.shape[1]
        freqs, _, spec = stft(audio, fs=sample_rate, nperseg=self.n_fft, noverlap=self.n_fft * 3 // 4)
        mag = np.abs(spec).mean(axis=0)  # shared mask across channels
        harm = median_filter(mag, size=(1, self.kernel))   # smooth along time
        perc = median_filter(mag, size=(self.kernel, 1))   # smooth along frequency
        eps = 1e-10
        m_perc = perc ** 2 / (perc ** 2 + harm ** 2 + eps)
        m_harm = 1.0 - m_perc
        low = (freqs < self.bass_cutoff_hz).astype(np.float32)[:, None]

        def inv(mask: np.ndarray) -> np.ndarray:
            _, x = istft(spec * mask[None], fs=sample_rate, nperseg=self.n_fft, noverlap=self.n_fft * 3 // 4)
            x = x[:, :n]
            return np.pad(x, ((0, 0), (0, n - x.shape[1]))).astype(np.float32)

        return {
            "drums": inv(m_perc),
            "bass": inv(m_harm * low),
            "other": inv(m_harm * (1.0 - low)),
        }
