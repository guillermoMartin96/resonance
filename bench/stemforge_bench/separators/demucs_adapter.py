"""Demucs (Hybrid Transformer Demucs v4) adapter.

Uses only `demucs.pretrained.get_model` + `demucs.apply.apply_model`, i.e. the model
path. `demucs.api` is deliberately not imported: it pulls in `sphn` for file decoding,
which has no Intel-macOS wheel (see docs/research/M0-environment.md).
Mirrors the input normalisation of `demucs.api.Separator.separate_tensor`.

Weights: `demucs.pretrained.get_model` would fetch the bag YAML and safetensors from
the Hugging Face hub at whatever revision is current, without checksums. Instead we
download each file at a pinned commit, verify its sha256, and only then build the
bag with demucs' own loaders. The pins are the files behind every committed result.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

import numpy as np

from ..audio import from_stereo, resample, to_stereo
from .base import SeparationError, SeparatorInfo, validate_input
from .mdx_onnx import verify_sha256

PINNED = {  # observed 2026-10-09 in adefossez/HTDemucs*; match weights_sha256 in bench/results
    "htdemucs": {
        "repo": "adefossez/HTDemucs",
        "revision": "cbc8a9b1a87023b7fd74e7b3412e6321c0eab003",
        "files": {
            "htdemucs.yaml": "239c445d0b14454d541ad8bd9bb271c9e536d267e8a4625208744cbb2e7bb66c",
            "955717e8.safetensors": "d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd",
        },
    },
    "htdemucs_ft": {
        "repo": "adefossez/HTDemucs-ft",
        "revision": "d74ac89c3a1e874fc78f152555cf4d8533f06cd4",
        "files": {
            "htdemucs_ft.yaml": "69470b8c1bbd674437b51bc9fb491327a10ab0396b702c93389b9cf750016346",
            "04573f0d.safetensors": "68854b0d7c2b3274723b5761f6fd9f5aec5f1bcd3f0de7c1669546fdb7871b7c",
            "92cfc3b6.safetensors": "a241863551f30d01c42bd7b97da40839922ead3acb0f1fcab25682f55b4eeb59",
            "d12395a8.safetensors": "5b01a97567ae9a3178a6236fb520251045c03eb8834bc8c24a4eec11d6c8fb56",
            "f7e0c4bc.safetensors": "2c85ab3c62dd6edd8e0b965e38b16fd1cdde357cc25de6b6bc9ce7c83f60925f",
        },
    },
}


def _hf_download(repo_id: str, filename: str, revision: str) -> str:
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo_id, filename, revision=revision)


def resolve_pinned_files(model_name: str, download: Callable[..., str] = _hf_download) -> dict[str, Path]:
    """Download (or reuse cached) pinned files and verify each sha256. Nothing is parsed
    or loaded until every file has been verified."""
    pin = PINNED.get(model_name)
    if pin is None:
        raise SeparationError(f"demucs model {model_name!r} is not pinned; add its revision and sha256s to PINNED")
    paths = {}
    for filename, sha in pin["files"].items():
        path = Path(download(pin["repo"], filename, revision=pin["revision"]))
        verify_sha256(path, sha)
        paths[filename] = path
    return paths


class DemucsSeparator:
    def __init__(self, model_name: str = "htdemucs", shifts: int = 1, overlap: float = 0.25,
                 seed: int = 0, threads: int | None = None) -> None:
        self.model_name, self.shifts, self.overlap, self.seed, self.threads = model_name, shifts, overlap, seed, threads
        self._model = None
        self.info = self._make_info(())

    def _make_info(self, hashes: tuple[str, ...], provenance: dict | None = None) -> SeparatorInfo:
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
            params={"shifts": self.shifts, "overlap": self.overlap, "seed": self.seed, "device": "cpu",
                    **(provenance or {})},
        )

    def load(self) -> None:
        if self._model is not None:
            return
        import torch
        import yaml
        from demucs.apply import BagOfModels
        from demucs.hf import load_safetensors_model

        if self.threads:
            torch.set_num_threads(self.threads)
        paths = resolve_pinned_files(self.model_name)
        bag = yaml.safe_load(paths[f"{self.model_name}.yaml"].read_text())
        models = [load_safetensors_model(paths[f"{sig}.safetensors"]) for sig in bag["models"]]
        self._model = BagOfModels(models, bag.get("weights"), bag.get("segment"))
        self._model.eval()
        pin = PINNED[self.model_name]
        self.info = self._make_info(tuple(f"{name}:{sha}" for name, sha in sorted(pin["files"].items())
                                          if name.endswith(".safetensors")),
                                    {"hf_repo": pin["repo"], "hf_revision": pin["revision"],
                                     "bag_yaml_sha256": pin["files"][f"{self.model_name}.yaml"]})

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
        # apply_model draws shift offsets from Python's global `random`; seed it for this
        # call only, and leave the caller's RNG state as it was.
        state = random.getstate()
        random.seed(self.seed)
        torch.manual_seed(self.seed)
        try:
            with torch.no_grad():
                out = apply_model(self._model, ((wav - mean) / std)[None], shifts=self.shifts,
                                  split=True, overlap=self.overlap, device="cpu", progress=False)
        finally:
            random.setstate(state)
        out = (out * std + mean)[0].numpy()
        stems = {}
        for name, est in zip(self._model.sources, out):
            est = resample(est, sr, sample_rate)
            est = np.pad(est, ((0, 0), (0, max(0, n - est.shape[1]))))[:, :n]
            stems[name] = from_stereo(est, channels).astype(np.float32)
        stems["accompaniment"] = stems["drums"] + stems["bass"] + stems["other"]
        return {role: stems[role] for role in self.info.roles}
