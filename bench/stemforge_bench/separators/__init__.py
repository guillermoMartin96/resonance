"""Separator registry. Adapters are constructed lazily so optional engines
(torch, onnxruntime) are only imported when selected."""
from __future__ import annotations

from typing import Callable

from .base import CANONICAL_ROLES, SeparationError, Separator, SeparatorInfo


def _demucs(name: str) -> Callable[[], Separator]:
    def make() -> Separator:
        from .demucs_adapter import DemucsSeparator
        return DemucsSeparator(name)
    return make


def _mdx(file: str) -> Callable[[], Separator]:
    def make() -> Separator:
        from .mdx_onnx import MDXOnnxSeparator
        return MDXOnnxSeparator(file)
    return make


def _baseline(kind: str) -> Callable[[], Separator]:
    def make() -> Separator:
        from .baselines import HPSSBaseline, MixtureBaseline
        return {"mixture": MixtureBaseline, "hpss": HPSSBaseline}[kind]()
    return make


REGISTRY: dict[str, Callable[[], Separator]] = {
    "baseline.mixture": _baseline("mixture"),
    "baseline.hpss": _baseline("hpss"),
    "demucs.htdemucs": _demucs("htdemucs"),
    "demucs.htdemucs_ft": _demucs("htdemucs_ft"),
    "mdx.Kim_Vocal_2": _mdx("Kim_Vocal_2.onnx"),
    "mdx.UVR-MDX-NET-Inst_HQ_3": _mdx("UVR-MDX-NET-Inst_HQ_3.onnx"),
}


def create(separator_id: str) -> Separator:
    try:
        return REGISTRY[separator_id]()
    except KeyError:
        raise SeparationError(f"unknown separator {separator_id!r}; known: {sorted(REGISTRY)}") from None


__all__ = ["CANONICAL_ROLES", "REGISTRY", "SeparationError", "Separator", "SeparatorInfo", "create"]
