"""Objective separation metrics (numpy only).

All metrics take arrays shaped (channels, samples) at the same sample rate.

- sdr: "global"/"new" SDR used by the Sony MDX'21 challenge and the Demucs v4 paper:
  10 log10(sum s^2 / sum (s - s_hat)^2). Not the filtered BSS Eval v4 SDR (museval).
- si_sdr: scale-invariant SDR (Le Roux et al. 2019), channels concatenated.
- decompose: instantaneous least-squares projection of the estimate onto *all*
  reference sources: s_hat = sum_j a_j s_j + e. Gives
    sir  = target energy vs. other-source energy   (higher = less bleed)
    sar  = explained energy vs. residual e         (higher = fewer artifacts)
    bleed_ratio = fraction of estimate energy attributable to other sources.
  Unlike BSS Eval this allows no FIR distortion, so phase/filtering changes are
  counted as artifacts. Treat as relative, not comparable to published SIR/SAR.
- silent_leak_db: in 1 s windows where the target is silent (< -50 dB re. its own
  peak window) but the mixture is not, estimate energy relative to mixture energy.
  "How loud is the leftover when the instrument isn't playing" -- the bleed a
  sampler hears when chopping a region. Lower is better; None if no such windows.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-10


def sdr(ref: np.ndarray, est: np.ndarray) -> float:
    num = np.sum(ref.astype(np.float64) ** 2)
    den = np.sum((ref.astype(np.float64) - est) ** 2)
    return float(10 * np.log10((num + EPS) / (den + EPS)))


def si_sdr(ref: np.ndarray, est: np.ndarray) -> float:
    r, e = ref.reshape(-1).astype(np.float64), est.reshape(-1).astype(np.float64)
    alpha = np.dot(e, r) / (np.dot(r, r) + EPS)
    target = alpha * r
    return float(10 * np.log10((np.sum(target ** 2) + EPS) / (np.sum((e - target) ** 2) + EPS)))


ATOMIC = ("vocals", "drums", "bass", "other")
GROUPS = {"accompaniment": ("drums", "bass", "other")}


def group(role: str) -> tuple[str, ...]:
    return GROUPS.get(role, (role,))


def reference(refs: dict[str, np.ndarray], role: str) -> np.ndarray:
    return sum(refs[k] for k in group(role))


def decompose(refs: dict[str, np.ndarray], role: str, est: np.ndarray) -> dict[str, float]:
    """refs must hold atomic sources only; role may be a group (accompaniment)."""
    names = [k for k in refs if np.sum(refs[k] ** 2) > EPS]
    targets = [k for k in group(role) if k in names]
    e = est.reshape(-1).astype(np.float64)
    if not targets:
        return {"sir": None, "sar": None, "bleed_ratio": None}
    basis = np.stack([refs[k].reshape(-1).astype(np.float64) for k in names], axis=1)
    coef, *_ = np.linalg.lstsq(basis, e, rcond=None)
    t = [names.index(k) for k in targets]
    s_target = basis[:, t] @ coef[t]
    s_interf = basis @ coef - s_target
    resid = e - basis @ coef
    et, ei, ea = np.sum(s_target ** 2), np.sum(s_interf ** 2), np.sum(resid ** 2)
    return {
        "sir": float(10 * np.log10((et + EPS) / (ei + EPS))),
        "sar": float(10 * np.log10((et + ei + EPS) / (ea + EPS))),
        "bleed_ratio": float(ei / (np.sum(e ** 2) + EPS)),
    }


def _window_energy(x: np.ndarray, win: int) -> np.ndarray:
    n = x.shape[-1] // win
    return np.sum(x[..., : n * win].reshape(x.shape[0], n, win) ** 2, axis=(0, 2))


def silent_leak_db(ref: np.ndarray, est: np.ndarray, mix: np.ndarray, sr: int) -> float | None:
    win = sr
    er, ee, em = _window_energy(ref, win), _window_energy(est, win), _window_energy(mix, win)
    if er.size == 0:
        return None
    ref_peak = er.max()
    silent = (er < ref_peak * 1e-5) | (ref_peak < EPS)
    silent &= em > em.max() * 1e-4
    if not np.any(silent):
        return None
    return float(10 * np.log10((ee[silent].sum() + EPS) / (em[silent].sum() + EPS)))


def evaluate_stem(refs: dict[str, np.ndarray], mix: np.ndarray, role: str, est: np.ndarray, sr: int) -> dict:
    ref = reference(refs, role)
    active = np.sum(ref ** 2) > EPS
    out = {
        "sdr": sdr(ref, est) if active else None,
        "si_sdr": si_sdr(ref, est) if active else None,
        "silent_leak_db": silent_leak_db(ref, est, mix, sr),
        "est_rms_dbfs": float(10 * np.log10(np.mean(est.astype(np.float64) ** 2) + EPS)),
    }
    out.update(decompose(refs, role, est))
    return out
