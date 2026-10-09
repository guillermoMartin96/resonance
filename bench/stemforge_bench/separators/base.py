"""Provider-neutral separation interface.

Every separation engine (ML model, classical DSP, remote worker) is wrapped in an
adapter that satisfies `Separator`. The rest of StemForge only sees this contract:
float32 numpy audio in, a dict of named stems out, plus metadata describing exactly
which implementation/weights produced them (for provenance and reproducibility).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

# Canonical stem roles. Adapters map their native outputs onto these names.
# "accompaniment" means everything except vocals (the 2-stem "instrumental").
CANONICAL_ROLES = ("vocals", "drums", "bass", "other", "accompaniment")


@dataclass(frozen=True)
class SeparatorInfo:
    id: str                      # stable adapter id, e.g. "demucs.htdemucs"
    engine: str                  # implementation family, e.g. "demucs", "mdx-onnx"
    engine_version: str          # package / implementation version
    model_name: str              # model or weights identifier
    native_sample_rate: int
    roles: tuple[str, ...]       # canonical roles this adapter emits
    code_license: str
    weights_license: str         # "unstated" is a valid, important answer
    weights_sha256: tuple[str, ...] = ()
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class SeparationError(RuntimeError):
    """Raised for actionable separation failures (bad input, missing weights...)."""


@runtime_checkable
class Separator(Protocol):
    info: SeparatorInfo

    def load(self) -> None:
        """Load weights / allocate resources. Idempotent."""

    def separate(self, audio: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]:
        """Separate `audio` (shape (channels, samples), float32, channels in {1, 2}).

        Returns {role: array} with every role in `info.roles`; each array has the
        same shape and sample rate as the input. Must not mutate `audio`.
        """


def validate_input(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    if not isinstance(audio, np.ndarray) or audio.ndim != 2:
        raise SeparationError("audio must be a 2-D array shaped (channels, samples)")
    if audio.shape[0] not in (1, 2):
        raise SeparationError(f"expected 1 or 2 channels, got {audio.shape[0]}")
    if audio.shape[1] == 0:
        raise SeparationError("audio is empty")
    if sample_rate <= 0:
        raise SeparationError("sample_rate must be positive")
    if not np.all(np.isfinite(audio)):
        raise SeparationError("audio contains NaN or Inf")
    return audio.astype(np.float32, copy=False)


def validate_output(info: SeparatorInfo, audio: np.ndarray, stems: dict[str, np.ndarray]) -> None:
    missing = set(info.roles) - set(stems)
    if missing:
        raise SeparationError(f"{info.id} did not return roles {sorted(missing)}")
    for role, stem in stems.items():
        if stem.shape != audio.shape:
            raise SeparationError(f"{info.id}:{role} shape {stem.shape} != input {audio.shape}")
        if not np.all(np.isfinite(stem)):
            raise SeparationError(f"{info.id}:{role} contains NaN or Inf")
