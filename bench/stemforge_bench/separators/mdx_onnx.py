"""MDX-Net (UVR-compatible) ONNX adapter: onnxruntime + numpy, no torch.

Re-implements the inference loop of `audio_separator.separator.architectures.
mdx_separator` (MIT, nomadkaraoke/python-audio-separator) because current releases
of that package require torch>=2.3 / numpy>=2, which do not exist for Intel macOS.

Algorithm (matching the reference with its defaults hop=1024, segment=256,
overlap=0.25, denoise off):
  chunk = hop * (segment - 1); trim = n_fft // 2
  for each Hann-weighted overlapping chunk: STFT (center, periodic Hann) ->
  keep first dim_f bins, zero bins 0..2 -> ONNX model -> ISTFT -> overlap-add.
The model predicts its *primary* stem; the complementary stem is
mix - primary * compensate (UVR's "compensate" factor, per-model).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..audio import from_stereo, resample, to_stereo
from .base import SeparationError, SeparatorInfo, validate_input

MODEL_DIR = Path(__file__).resolve().parents[2] / ".cache" / "models" / "mdx"
DOWNLOAD_URL = "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/{name}"
PARAMS_URL = "https://raw.githubusercontent.com/TRvlvr/application_data/main/mdx_model_data/model_data_new.json"
SAMPLE_RATE = 44100


def uvr_model_hash(path: Path) -> str:
    """UVR keys model params by md5 of the last 10000*1024 bytes of the file."""
    with open(path, "rb") as f:
        try:
            f.seek(-10000 * 1024, 2)
        except OSError:
            f.seek(0)
        return hashlib.md5(f.read()).hexdigest()


def stft(x: np.ndarray, n_fft: int, hop: int, window: np.ndarray) -> np.ndarray:
    """torch.stft(center=True, pad_mode='reflect') equivalent. x: (..., n) -> (..., bins, frames)."""
    pad = n_fft // 2
    xp = np.pad(x, [(0, 0)] * (x.ndim - 1) + [(pad, pad)], mode="reflect")
    n_frames = 1 + (xp.shape[-1] - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = xp[..., idx] * window          # (..., frames, n_fft)
    return np.swapaxes(np.fft.rfft(frames, axis=-1), -1, -2)


def istft(spec: np.ndarray, n_fft: int, hop: int, window: np.ndarray) -> np.ndarray:
    """torch.istft(center=True) equivalent without explicit length."""
    frames = np.fft.irfft(np.swapaxes(spec, -1, -2), n=n_fft, axis=-1) * window
    n_frames = frames.shape[-2]
    total = n_fft + hop * (n_frames - 1)
    out = np.zeros(frames.shape[:-2] + (total,), dtype=np.float64)
    norm = np.zeros(total, dtype=np.float64)
    wsq = window ** 2
    for i in range(n_frames):
        out[..., i * hop:i * hop + n_fft] += frames[..., i, :]
        norm[i * hop:i * hop + n_fft] += wsq
    pad = n_fft // 2
    out, norm = out[..., pad:total - pad], norm[pad:total - pad]
    return out / np.where(norm > 1e-11, norm, 1.0)


class MDXOnnxSeparator:
    def __init__(self, model_file: str, hop: int = 1024, segment: int = 256, overlap: float = 0.25,
                 threads: int | None = None, model_dir: Path = MODEL_DIR) -> None:
        self.model_file, self.hop, self.segment, self.overlap, self.threads = model_file, hop, segment, overlap, threads
        self.path = model_dir / model_file
        self._session = None
        self._params: dict | None = None
        self.info = self._make_info("", {})

    def _make_info(self, sha: str, params: dict) -> SeparatorInfo:
        try:
            import onnxruntime
            version = f"stemforge-mdx-1/onnxruntime-{onnxruntime.__version__}"
        except ImportError:
            version = "onnxruntime-not-installed"
        return SeparatorInfo(
            id=f"mdx.{Path(self.model_file).stem}", engine="mdx-onnx", engine_version=version,
            model_name=self.model_file, native_sample_rate=SAMPLE_RATE,
            roles=("vocals", "accompaniment"), code_license="MIT (algorithm from audio-separator/UVR)",
            weights_license="unstated (TRvlvr/model_repo has no LICENSE; trainer/training data undisclosed)",
            weights_sha256=(sha,) if sha else (),
            params={"hop": self.hop, "segment": self.segment, "overlap": self.overlap, **params},
        )

    def load(self) -> None:
        if self._session is not None:
            return
        import onnxruntime as ort

        if not self.path.exists():
            raise SeparationError(f"model weights not found at {self.path}; run scripts/fetch_models.py")
        table = json.loads((self.path.parent / "model_data.json").read_text())
        params = table.get(uvr_model_hash(self.path))
        if params is None:
            raise SeparationError(f"no UVR parameters for {self.model_file}")
        self._params = params
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        if self.threads:
            opts.intra_op_num_threads = self.threads
        self._session = ort.InferenceSession(str(self.path), sess_options=opts, providers=["CPUExecutionProvider"])
        sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.info = self._make_info(sha, params)

    def _demix(self, mix: np.ndarray) -> np.ndarray:
        p = self._params
        n_fft, dim_f, hop = p["mdx_n_fft_scale_set"], p["mdx_dim_f_set"], self.hop
        window = np.hanning(n_fft + 1)[:-1]  # periodic Hann, as torch.hann_window(periodic=True)
        trim = n_fft // 2
        chunk = hop * (self.segment - 1)
        gen = chunk - 2 * trim
        pad = gen + trim - (mix.shape[-1] % gen)
        mixture = np.concatenate([np.zeros((2, trim)), mix, np.zeros((2, pad))], axis=1)
        step = int((1 - self.overlap) * chunk)
        result = np.zeros_like(mixture)
        divider = np.zeros_like(mixture)
        input_name = self._session.get_inputs()[0].name
        for start in range(0, mixture.shape[-1], step):
            end = min(start + chunk, mixture.shape[-1])
            part = mixture[:, start:end]
            if part.shape[-1] < chunk:
                part = np.pad(part, ((0, 0), (0, chunk - part.shape[-1])))
            spec = stft(part, n_fft, hop, window)[:, :dim_f, :]            # (2, dim_f, T) complex
            x = np.stack([spec.real, spec.imag], axis=1).reshape(4, dim_f, -1)  # L.re, L.im, R.re, R.im
            x[:, :3, :] = 0
            y = self._session.run(None, {input_name: x[None].astype(np.float32)})[0][0]
            y = y.reshape(2, 2, dim_f, -1)
            full = np.zeros((2, n_fft // 2 + 1, y.shape[-1]), dtype=np.complex128)
            full[:, :dim_f, :] = y[:, 0] + 1j * y[:, 1]
            wave = istft(full, n_fft, hop, window)[:, :end - start]
            w = np.hanning(end - start) if self.overlap else np.ones(end - start)
            result[:, start:end] += wave * w
            divider[:, start:end] += w
        out = result / np.where(divider > 1e-8, divider, 1.0)
        return out[:, trim:trim + mix.shape[-1]]

    def separate(self, audio: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        audio = validate_input(audio, sample_rate)
        self.load()
        channels, n = audio.shape
        mix = resample(to_stereo(audio), sample_rate, SAMPLE_RATE).astype(np.float64)
        peak = float(np.abs(mix).max())
        if peak < 1e-9:
            primary = np.zeros_like(mix)
        else:
            primary = self._demix(mix / peak) * peak
        secondary = mix - primary * self._params["compensate"]
        if self._params["primary_stem"].lower() == "vocals":
            vocals, acc = primary, secondary
        else:
            acc, vocals = primary, secondary

        def back(x: np.ndarray) -> np.ndarray:
            x = resample(x, SAMPLE_RATE, sample_rate)
            x = np.pad(x, ((0, 0), (0, max(0, n - x.shape[1]))))[:, :n]
            return from_stereo(x, channels).astype(np.float32)

        return {"vocals": back(vocals), "accompaniment": back(acc)}
