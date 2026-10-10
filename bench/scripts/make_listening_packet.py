"""Build a blinded listening packet from saved outputs (run.py --save-audio).

    python scripts/make_listening_packet.py --dataset vocalmix --split dev --role vocals

Writes .cache/listening/<dataset>/<split>/<role>/:
  <item>/mixture.wav      the input mix, unmodified (for orientation)
  <item>/A.wav, B.wav...  every separator's estimate for --role under random labels,
                          loudness-matched (same RMS per item) so level can't give them away
  ratings.csv             one blank row per (item, label) for the rubric in
                          docs/research/LISTENING_TEST.md
The label -> separator key goes OUTSIDE the packet, to
.cache/listening_keys/<dataset>/<split>/<role>/KEY.json -- don't open it until
ratings.csv is filled in. Re-running replaces the packet (and re-randomises unless
--seed is given; the seed used is recorded in the key).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import secrets
import shutil
import string
import sys
from pathlib import Path

import numpy as np

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))
from stemforge_bench.audio import read_audio, write_audio  # noqa: E402

TARGET_RMS_DBFS = -23.0
PEAK_CEILING = 0.99           # leave headroom for PCM_16 rounding
SILENT_RMS = 1e-6             # estimates quieter than this are copied without gain
RATING_FIELDS = ["item", "label", "isolation", "integrity", "artifacts", "usable",
                 "failure_timestamps", "notes"]


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def build_packet(src: Path, dst: Path, key_path: Path, role: str, seed: int | None = None) -> dict:
    """Blind every `<item>/<separator>__<role>.wav` under `src` into `dst`; key to `key_path`."""
    if key_path.resolve().is_relative_to(dst.resolve()):
        raise ValueError("key_path must be outside the packet directory")
    if seed is None:
        seed = secrets.randbits(32)
    rng = random.Random(seed)
    if dst.exists():
        shutil.rmtree(dst)  # no stale labels from an earlier run
    dst.mkdir(parents=True)
    key: dict = {"role": role, "seed": seed, "target_rms_dbfs": TARGET_RMS_DBFS, "items": {}}
    rows = []
    for item_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        estimates = sorted(item_dir.glob(f"*__{role}.wav"))
        if not estimates:
            continue
        out = dst / item_dir.name
        out.mkdir()
        shutil.copy(item_dir / "mixture.wav", out / "mixture.wav")
        audio = [read_audio(p) for p in estimates]
        # One common RMS for the item, lowered if needed so no candidate clips.
        target = 10 ** (TARGET_RMS_DBFS / 20)
        for x, _ in audio:
            r, peak = _rms(x), float(np.abs(x).max())
            if r > SILENT_RMS:
                target = min(target, PEAK_CEILING * r / peak)
        labels = list(string.ascii_uppercase[: len(estimates)])
        rng.shuffle(labels)
        key["items"][item_dir.name] = {}
        for label, path, (x, sr) in zip(labels, estimates, audio):
            r = _rms(x)
            gain = target / r if r > SILENT_RMS else 1.0
            write_audio(out / f"{label}.wav", (x * gain).astype(np.float32), sr)
            key["items"][item_dir.name][label] = {"separator": path.name.split("__")[0],
                                                  "gain_db": round(float(20 * np.log10(gain)), 2)}
        rows += [{"item": item_dir.name, "label": lb} for lb in sorted(labels)]
    with (dst / "ratings.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RATING_FIELDS)
        w.writeheader()
        w.writerows(rows)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps(key, indent=2))
    return key


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--role", required=True)
    ap.add_argument("--seed", type=int, default=None, help="omit for a fresh random blinding")
    args = ap.parse_args()
    src = BENCH / ".cache" / "outputs" / args.dataset / args.split
    dst = BENCH / ".cache" / "listening" / args.dataset / args.split / args.role
    key_path = BENCH / ".cache" / "listening_keys" / args.dataset / args.split / args.role / "KEY.json"
    if not src.exists():
        ap.error(f"no saved outputs in {src}; run stemforge_bench.run with --save-audio first")
    key = build_packet(src, dst, key_path, args.role, args.seed)
    print(f"packet in {dst} ({len(key['items'])} items); ratings sheet {dst / 'ratings.csv'}")
    print(f"key (do not open before rating): {key_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
