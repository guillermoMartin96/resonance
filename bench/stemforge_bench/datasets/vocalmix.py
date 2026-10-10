"""Real recorded vocals over BabySlakh accompaniment ("vocalmix").

Each item = one unaccompanied vocal recording (Wikimedia Commons, CC0 / public
domain / CC BY-SA, see data/manifest.json) + one BabySlakh accompaniment from the
same split. Everything is mono 16 kHz (BabySlakh's rate), so a model cannot find the
vocal merely by its extra bandwidth. Vocal active-RMS is matched to accompaniment
active-RMS (0 dB vocal-to-accompaniment ratio), then the mix peak is set to 0.8.

Limitations: vocals and accompaniment are not musically related (key/tempo
mismatch); some recordings include room reverb, which is part of the "vocals"
ground truth. Choirs are counted as a single vocal stem (as in MUSDB18).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..audio import read_audio, resample
from . import slakh
from .procedural import Item

BENCH = Path(__file__).resolve().parents[2]
MANIFEST = BENCH / "data" / "manifest.json"
VOCAL_DIR = BENCH / ".cache" / "acappellas"
SR = 16000
EXCERPT_S = 30.0
PAIRS_PER_VOCAL = 2


def _active_rms(x: np.ndarray, sr: int) -> float:
    win = sr // 10
    n = x.shape[-1] // win
    e = np.mean(x[..., : n * win].reshape(x.shape[0], n, win) ** 2, axis=(0, 2))
    active = e > e.max() * 1e-3
    return float(np.sqrt(e[active].mean())) if active.any() else 0.0


def _vocal_excerpt(x: np.ndarray, sr: int) -> np.ndarray:
    win, hop, sec = int(EXCERPT_S * sr), sr, sr
    if x.shape[1] <= win:
        return np.pad(x, ((0, 0), (0, win - x.shape[1])))
    n = x.shape[1] // sec
    e = np.mean(x[:, : n * sec].reshape(x.shape[0], n, sec) ** 2, axis=(0, 2))
    active = e > e.max() * 1e-4
    w = int(EXCERPT_S)
    best = max(range(0, n - w + 1), key=lambda s: (active[s:s + w].sum(), -s))
    return x[:, best * sec: best * sec + win]


def load(split: str) -> list[Item]:
    manifest = json.loads(MANIFEST.read_text())
    vocals = [a for a in manifest["acappellas"] if a["split"] == split]
    tracks = slakh.load(split)
    if not tracks:
        raise FileNotFoundError("no BabySlakh tracks available; run scripts/fetch_data.py")
    items = []
    for vi, meta in enumerate(vocals):
        path = next(VOCAL_DIR.glob(meta["id"] + ".*"), None)
        if path is None:
            raise FileNotFoundError(f"missing vocal {meta['id']}; run scripts/fetch_data.py")
        audio, sr = read_audio(path)
        voc = _vocal_excerpt(resample(audio.mean(axis=0, keepdims=True), sr, SR), SR)
        for k in range(PAIRS_PER_VOCAL):
            acc_item = tracks[(vi * PAIRS_PER_VOCAL + k) % len(tracks)]
            acc = {s: acc_item.stems[s] for s in ("drums", "bass", "other")}
            n = min(voc.shape[1], acc["drums"].shape[1])
            acc = {s: v[:, :n].astype(np.float64) for s, v in acc.items()}
            v = voc[:, :n].astype(np.float64)
            v *= _active_rms(sum(acc.values()), SR) / max(_active_rms(v, SR), 1e-9)
            stems = {"vocals": v, **acc}
            scale = 0.8 / max(np.abs(sum(stems.values())).max(), 1e-9)
            stems = {s: (x * scale).astype(np.float32) for s, x in stems.items()}
            items.append(Item(
                id=f"vocalmix-{meta['id']}+{acc_item.id.removeprefix('babyslakh-')}",
                sample_rate=SR, stems=stems,
                license=f"vocals: {meta['license']}; accompaniment: {acc_item.license}",
                attribution=f"{meta['attribution']}; {acc_item.attribution}",
            ))
    return items
