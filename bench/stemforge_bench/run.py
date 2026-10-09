"""Run one separator over one dataset split and write a JSON result.

    python -m stemforge_bench.run --dataset babyslakh --split dev --separator demucs.htdemucs

Holdout splits additionally require --frozen-config config/frozen.json; its sha256
is stored in the result so holdout scores are tied to a configuration fixed in advance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from .audio import write_audio
from .datasets import DATASETS
from .metrics import evaluate_stem
from .separators import create
from .separators.base import validate_output

BENCH = Path(__file__).resolve().parents[1]


def rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / 1e6 if sys.platform == "darwin" else peak / 1e3  # bytes on macOS, KiB on Linux


def git_rev() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=BENCH, capture_output=True,
                              text=True, check=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=sorted(DATASETS))
    ap.add_argument("--split", required=True, choices=["dev", "holdout"])
    ap.add_argument("--separator", required=True)
    ap.add_argument("--out", type=Path, default=BENCH / "results")
    ap.add_argument("--frozen-config", type=Path)
    ap.add_argument("--save-audio", action="store_true", help="write estimates under .cache/outputs for listening")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    frozen_sha = None
    if args.split == "holdout":
        if not args.frozen_config or not args.frozen_config.exists():
            ap.error("holdout runs require --frozen-config (fixed before scoring)")
        cfg = json.loads(args.frozen_config.read_text())
        if args.separator not in cfg["separators"]:
            ap.error(f"{args.separator} is not in the frozen config")
        frozen_sha = hashlib.sha256(args.frozen_config.read_bytes()).hexdigest()

    t0 = time.perf_counter()
    items = DATASETS[args.dataset](args.split)
    if args.limit:
        items = items[: args.limit]
    data_s = time.perf_counter() - t0
    rss_before_model = rss_mb()

    sep = create(args.separator)
    t0 = time.perf_counter()
    sep.load()
    load_s = time.perf_counter() - t0
    rss_after_load = rss_mb()

    results = []
    for item in items:
        mix = item.mixture
        dur = mix.shape[1] / item.sample_rate
        t0 = time.perf_counter()
        stems = sep.separate(mix, item.sample_rate)
        sep_s = time.perf_counter() - t0
        validate_output(sep.info, mix, stems)
        metrics = {role: evaluate_stem(item.stems, mix, role, est, item.sample_rate)
                   for role, est in stems.items()}
        results.append({"item": item.id, "license": item.license, "duration_s": dur,
                        "separate_s": sep_s, "rtf": sep_s / dur, "metrics": metrics})
        if args.save_audio:
            out_dir = BENCH / ".cache" / "outputs" / args.dataset / args.split / item.id
            write_audio(out_dir / "mixture.wav", mix, item.sample_rate)
            for role, est in stems.items():
                write_audio(out_dir / f"{args.separator}__{role}.wav", est, item.sample_rate)
        print(f"{args.separator} {item.id} rtf={sep_s / dur:.3f} " +
              " ".join(f"{r}:sdr={m['sdr']:.2f}" for r, m in metrics.items() if m["sdr"] is not None),
              flush=True)

    import numpy, scipy  # noqa: E401 - versions for the record
    record = {
        "separator": sep.info.to_dict(),
        "dataset": args.dataset, "split": args.split, "n_items": len(results),
        "frozen_config_sha256": frozen_sha, "git_rev": git_rev(),
        "env": {"python": platform.python_version(), "machine": platform.machine(),
                "platform": platform.platform(), "processor": platform.processor(),
                "numpy": numpy.__version__, "scipy": scipy.__version__},
        "timing": {"dataset_load_s": data_s, "model_load_s": load_s,
                   "total_separate_s": sum(r["separate_s"] for r in results),
                   "total_audio_s": sum(r["duration_s"] for r in results)},
        "memory_mb": {"peak_before_model": rss_before_model, "peak_after_load": rss_after_load,
                      "peak_total": rss_mb()},
        "items": results,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{args.dataset}__{args.split}__{args.separator}.json"
    path.write_text(json.dumps(record, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else str(o)))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
