"""Runtime/memory probe on a long input, one fresh process per separator.

    python scripts/perf_probe.py --seconds 180 --threads 8
Writes results/perf__<seconds>s.json. Peak RSS includes the Python interpreter,
the imported runtime (torch / onnxruntime) and the model weights.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
CHILD = r"""
import json, os, resource, sys, time
sys.path.insert(0, {bench!r})
t0 = time.perf_counter()
from stemforge_bench.audio import read_audio
from stemforge_bench.separators import create
mix, sr = read_audio({wav!r})
rss_data = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
sep = create({sid!r})
t1 = time.perf_counter(); sep.load(); load_s = time.perf_counter() - t1
rss_load = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
t2 = time.perf_counter(); sep.separate(mix, sr); sep_s = time.perf_counter() - t2
print(json.dumps({{"separator": {sid!r}, "audio_s": {seconds}, "load_s": load_s, "separate_s": sep_s,
                  "rtf": sep_s / {seconds}, "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
                  "rss_after_data_mb": rss_data, "rss_after_load_mb": rss_load}}))
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=180)
    ap.add_argument("--threads", type=int, default=0, help="OMP/MKL thread cap (0 = library default)")
    ap.add_argument("--separators", nargs="+", default=["baseline.hpss", "mdx.Kim_Vocal_2", "demucs.htdemucs"])
    args = ap.parse_args()
    env = None
    if args.threads:
        import os
        env = {**os.environ, "OMP_NUM_THREADS": str(args.threads), "MKL_NUM_THREADS": str(args.threads)}
    sys.path.insert(0, str(BENCH))
    from stemforge_bench.audio import write_audio
    from stemforge_bench.datasets.procedural import make_item
    wav = BENCH / ".cache" / f"perf_input_{args.seconds}s.wav"
    if not wav.exists():
        item = make_item(7, seconds=args.seconds)  # deterministic, CC0
        write_audio(wav, item.mixture, item.sample_rate)
    rows = []
    for sid in args.separators:
        code = CHILD.format(bench=str(BENCH), seconds=args.seconds, sid=sid, wav=str(wav))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=3600)
        if out.returncode != 0:
            rows.append({"separator": sid, "error": out.stderr[-2000:]})
        else:
            rows.append(json.loads(out.stdout.strip().splitlines()[-1]))
        print(json.dumps(rows[-1]), flush=True)
    path = BENCH / "results" / f"perf__{args.seconds}s{'__t' + str(args.threads) if args.threads else ''}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
