"""Demucs (Hybrid Transformer Demucs v4) adapter.

Uses only `demucs.pretrained.get_model` + `demucs.apply.apply_model`, i.e. the model
path. `demucs.api` is deliberately not imported: it pulls in `sphn` for file decoding,
which has no Intel-macOS wheel (see docs/research/M0-environment.md).
Mirrors the input normalisation of `demucs.api.Separator.separate_tensor`.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from ..audio import from_stereo, resample, to_stereo
from .base import SeparatorInfo, validate_input


class DemucsSeparator:
    def __init__(self, model_name: str = "htdemucs", shifts: int = 1, overlap: float = 0.25,
                 seed: int = 0, threads: int | None = None) -> None:
        self.model_name, self.shifts, self.overlap, self.seed, self.threads = model_name, shifts, overlap, seed, threads
        self._model = None
        self.info = self._make_info(())

    def _make_info(self, hashes: tuple[str, ...]) -> SeparatorInfo:
        try:
            import demucs
            version = demucs.__version__
        except ImportError:
            version = "not-installed"
        return SeparatorInfo(
            id=f"demucs.{self.model_name}", engine="demucs", engine_version=version,
            model_name=self.model_name, native_sample_rate=44100,
            roles=("vocals", "drums", "bass", "other", "accompaniment"),
            code_license="MIT",
            weights_license="unstated (HF adefossez/* model cards carry no license; trained on MUSDB18-HQ + ~800 undisclosed songs)",
            weights_sha256=hashes,
            params={"shifts": self.shifts, "overlap": self.overlap, "seed": self.seed, "device": "cpu"},
        )

    def load(self) -> None:
        if self._model is not None:
            return
        import torch
        from demucs.pretrained import get_model

        if self.threads:
            torch.set_num_threads(self.threads)
        self._model = get_model(self.model_name)
        self._model.eval()
        self.info = self._make_info(self._weight_hashes())

    def _weight_hashes(self) -> tuple[str, ...]:
        # Weights live in the HuggingFace cache; hash whatever safetensors were resolved.
        cache = Path.home() / ".cache" / "huggingface" / "hub"
        repo = {"htdemucs": "HTDemucs"}.get(self.model_name, "HTDemucs-" + self.model_name.removeprefix("htdemucs_"))
        snap = cache / f"models--adefossez--{repo}" / "snapshots"
        files = sorted(snap.glob("*/*.safetensors")) if snap.exists() else []
        return tuple(f"{f.name}:{hashlib.sha256(f.read_bytes()).hexdigest()}" for f in files)

    def separate(self, audio: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        import torch
        from demucs.apply import apply_model

        audio = validate_input(audio, sample_rate)
        self.load()
        channels, n = audio.shape
        sr = self._model.samplerate
        x = resample(to_stereo(audio), sample_rate, sr)
        wav = torch.from_numpy(np.ascontiguousarray(x))
        ref = wav.mean(0)
        mean, std = ref.mean(), ref.std() + 1e-8
        torch.manual_seed(self.seed)  # shifts use random offsets; seed for reproducibility
        with torch.no_grad():
            out = apply_model(self._model, ((wav - mean) / std)[None], shifts=self.shifts,
                              split=True, overlap=self.overlap, device="cpu", progress=False)
        out = (out * std + mean)[0].numpy()
        stems = {}
        for name, est in zip(self._model.sources, out):
            est = resample(est, sr, sample_rate)
            est = np.pad(est, ((0, 0), (0, max(0, n - est.shape[1]))))[:, :n]
            stems[name] = from_stereo(est, channels).astype(np.float32)
        stems["accompaniment"] = stems["drums"] + stems["bass"] + stems["other"]
        return {role: stems[role] for role in self.info.roles}
