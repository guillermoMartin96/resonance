"""Build a blinded listening packet from saved outputs (run.py --save-audio).

    python scripts/make_listening_packet.py --dataset vocalmix --split dev --role vocals
Copies each item's mixture plus every separator's estimate for --role into
.cache/listening/<dataset>/<split>/<role>/<item>/ under random labels (A, B, ...).
The label->separator key goes to .cache/listening/<...>/KEY.json -- don't open it
until the ratings are written down.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import string
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--role", required=True)
    ap.add_argument("--seed", type=int, default=None, help="omit for a fresh random blinding")
    args = ap.parse_args()
    src = BENCH / ".cache" / "outputs" / args.dataset / args.split
    dst = BENCH / ".cache" / "listening" / args.dataset / args.split / args.role
    if not src.exists():
        ap.error(f"no saved outputs in {src}; run stemforge_bench.run with --save-audio first")
    rng = random.Random(args.seed)
    key = {}
    for item_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        estimates = sorted(item_dir.glob(f"*__{args.role}.wav"))
        if not estimates:
            continue
        out = dst / item_dir.name
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy(item_dir / "mixture.wav", out / "mixture.wav")
        labels = list(string.ascii_uppercase[: len(estimates)])
        rng.shuffle(labels)
        key[item_dir.name] = {}
        for label, est in zip(labels, estimates):
            shutil.copy(est, out / f"{label}.wav")
            key[item_dir.name][label] = est.name.split("__")[0]
    (dst / "KEY.json").write_text(json.dumps(key, indent=2))
    print(f"packet in {dst} ({len(key)} items); key in {dst / 'KEY.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
