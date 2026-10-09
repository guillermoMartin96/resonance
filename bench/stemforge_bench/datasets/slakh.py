"""BabySlakh loader (CC BY 4.0).

BabySlakh = first 20 tracks of Slakh2100 (Manilow et al., WASPAA 2019), rendered
from Lakh MIDI with sample-based virtual instruments, 16 kHz mono WAV.
Source: https://zenodo.org/records/4603870 (md5 311096dc2bde7d61c97e930edbfc7f78).
Attribution: "Slakh2100 / BabySlakh by Ethan Manilow, Gordon Wichern, Prem Seetharaman,
Jonathan Le Roux, licensed CC BY 4.0".

Stems are grouped into drums (is_drum), bass (inst_class == "Bass") and other.
There are no vocals. Mixture = exact sum of grouped stems, so ground truth is exact.
A fixed 30 s excerpt per track is chosen deterministically (window maximising the
quietest group's energy) so all three groups are present.

Split (fixed before any model was run; never tune on holdout):
  dev     = Track00001..Track00005
  holdout = Track00006..Track00020
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from ..audio import read_audio
from .procedural import Item

ROOT = Path(__file__).resolve().parents[2] / ".cache" / "babyslakh" / "babyslakh_16k"
DEV = [f"Track{i:05d}" for i in range(1, 6)]
HOLDOUT = [f"Track{i:05d}" for i in range(6, 21)]
EXCERPT_S = 30.0
ATTRIBUTION = ("BabySlakh/Slakh2100 by E. Manilow, G. Wichern, P. Seetharaman, J. Le Roux "
               "(CC BY 4.0), https://zenodo.org/records/4603870")


def _group(meta: dict) -> str:
    if meta.get("is_drum"):
        return "drums"
    if str(meta.get("inst_class", "")).lower() == "bass":
        return "bass"
    return "other"


def load_track(track_dir: Path, excerpt_s: float | None = EXCERPT_S) -> Item | None:
    meta = yaml.safe_load((track_dir / "metadata.yaml").read_text())
    groups: dict[str, np.ndarray] = {}
    sr = None
    for stem_id, sm in sorted(meta["stems"].items()):
        path = track_dir / "stems" / f"{stem_id}.wav"
        if not path.exists():
            continue
        audio, sr = read_audio(path)
        g = _group(sm)
        if g in groups:
            n = max(groups[g].shape[1], audio.shape[1])
            groups[g] = np.pad(groups[g], ((0, 0), (0, n - groups[g].shape[1]))) + \
                np.pad(audio, ((0, 0), (0, n - audio.shape[1])))
        else:
            groups[g] = audio
    if sr is None or not {"drums", "bass", "other"} <= set(groups):
        return None
    n = max(v.shape[1] for v in groups.values())
    groups = {k: np.pad(v, ((0, 0), (0, n - v.shape[1]))) for k, v in groups.items()}
    if excerpt_s:
        win, hop = int(excerpt_s * sr), int(5 * sr)
        best, best_start = -np.inf, 0
        for start in range(0, max(1, n - win), hop):
            score = min(float(np.sum(v[:, start:start + win] ** 2)) for v in groups.values())
            if score > best:
                best, best_start = score, start
        groups = {k: v[:, best_start:best_start + win] for k, v in groups.items()}
    stems = {"vocals": np.zeros_like(groups["drums"]), **groups}
    peak = np.abs(sum(stems.values())).max()
    scale = 0.8 / max(peak, 1e-9)  # same gain on all stems keeps ground truth exact
    stems = {k: (v * scale).astype(np.float32) for k, v in stems.items()}
    return Item(id=f"babyslakh-{track_dir.name}", sample_rate=sr, stems=stems,
                license="CC-BY-4.0", attribution=ATTRIBUTION)


def load(split: str, root: Path = ROOT, excerpt_s: float | None = EXCERPT_S) -> list[Item]:
    names = {"dev": DEV, "holdout": HOLDOUT}[split]
    if not root.exists():
        raise FileNotFoundError(f"BabySlakh not found at {root}; run scripts/fetch_data.py")
    items = [load_track(root / name, excerpt_s) for name in names]
    return [i for i in items if i is not None]
