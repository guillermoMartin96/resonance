"""Run one separator over one dataset split and write a JSON result.

    python -m stemforge_bench.run --dataset babyslakh --split dev --separator demucs.htdemucs

Holdout splits additionally require --frozen-config config/frozen.json. Before anything
runs, every setting in it is checked against what will actually execute (separator
params, dataset seeds/tracks/vocals/durations), and the harness source must be clean in
git. The config's sha256, the git revision, and a sha256 of every input item are stored
in the result, so a holdout score is tied to a configuration fixed in advance and to the
exact audio scored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from .audio import write_audio
from .datasets import DATASETS
from .datasets import procedural, slakh, vocalmix
from .metrics import evaluate_stem
from .platform_info import peak_rss_mb as rss_mb
from .separators import create
from .separators.base import Separator, validate_output

BENCH = Path(__file__).resolve().parents[1]
SOURCE_PATHS = ["stemforge_bench", "config", "data"]  # what a holdout run must not have dirty


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=BENCH, capture_output=True,
                              text=True, check=True, timeout=10).stdout.strip()
    except Exception:
        return None


def git_rev() -> str:
    return _git("rev-parse", "HEAD") or "unknown"


def git_dirty() -> bool | None:
    out = _git("status", "--porcelain", "--", *SOURCE_PATHS)
    return None if out is None else bool(out)


def item_digest(item) -> str:
    """sha256 over sample rate and every stem's float32 samples, in sorted role order."""
    h = hashlib.sha256(str(item.sample_rate).encode())
    for role in sorted(item.stems):
        a = np.ascontiguousarray(item.stems[role], dtype=np.float32)
        h.update(role.encode() + str(a.shape).encode() + a.tobytes())
    return h.hexdigest()


def _slakh_range(spec: str) -> list[str]:
    lo, hi = (int(s.removeprefix("Track")) for s in spec.split("-"))
    return [f"Track{i:05d}" for i in range(lo, hi + 1)]


def _expect(what: str, frozen, actual) -> None:
    if frozen != actual:
        raise ValueError(f"frozen config mismatch for {what}: frozen={frozen!r}, code={actual!r}")


# Complete schema of an execution-relevant frozen config. Every tunable parameter must be
# frozen explicitly, so a changed adapter default can't slip in through an omitted key.
TOP_LEVEL_KEYS = {"frozen_at", "rationale", "separators", "datasets", "metrics_module"}
DATASET_KEYS = {"procedural": {"holdout_seeds", "seconds"},
                "babyslakh": {"holdout", "excerpt_s"},
                "vocalmix": {"holdout_vocals", "pairs_per_vocal"}}
SEPARATOR_KEYS = {"baseline.mixture": set(), "baseline.hpss": {"n_fft", "kernel", "bass_cutoff_hz"},
                  "demucs": {"shifts", "overlap", "seed", "device"}, "mdx": {"hop", "segment", "overlap"}}
METRICS_MODULE = "stemforge_bench/metrics.py"


def _keys(what: str, actual, expected: set) -> None:
    if set(actual) != expected:
        raise ValueError(f"frozen config {what}: keys {sorted(actual)} != expected {sorted(expected)}")


def check_frozen(cfg: dict, dataset: str, sep: Separator) -> None:
    """Raise ValueError unless the frozen config describes exactly what will run."""
    _keys("top level", cfg, TOP_LEVEL_KEYS)
    _expect("metrics_module", cfg["metrics_module"], METRICS_MODULE)
    from . import metrics
    if Path(metrics.__file__).resolve() != (BENCH / METRICS_MODULE).resolve():
        raise ValueError(f"imported metrics module {metrics.__file__} is not {METRICS_MODULE}")
    _keys("datasets", cfg["datasets"], set(DATASET_KEYS))
    for name, keys in DATASET_KEYS.items():
        _keys(f"datasets.{name}", cfg["datasets"][name], keys)
    sid = sep.info.id
    if sid not in cfg["separators"]:
        raise ValueError(f"{sid} is not in the frozen config")
    for other, params in cfg["separators"].items():
        family = other if other.startswith("baseline.") else other.split(".")[0]
        if family not in SEPARATOR_KEYS:
            raise ValueError(f"frozen config has unknown separator {other}")
        _keys(f"separators.{other}", params, SEPARATOR_KEYS[family])
    for key, value in cfg["separators"][sid].items():
        if key not in sep.info.params:
            raise ValueError(f"frozen param {sid}.{key} is not a parameter of the adapter")
        _expect(f"{sid}.{key}", value, sep.info.params[key])
    ds = cfg["datasets"]
    needed = {"procedural": ["procedural"], "babyslakh": ["babyslakh"],
              "vocalmix": ["babyslakh", "vocalmix"]}[dataset]
    if "procedural" in needed:
        _expect("procedural.holdout_seeds", list(ds["procedural"]["holdout_seeds"]), list(procedural.HOLDOUT_SEEDS))
        _expect("procedural.seconds", float(ds["procedural"]["seconds"]), procedural.SECONDS)
    if "babyslakh" in needed:
        _expect("babyslakh.holdout", _slakh_range(ds["babyslakh"]["holdout"]), slakh.HOLDOUT)
        _expect("babyslakh.excerpt_s", float(ds["babyslakh"]["excerpt_s"]), slakh.EXCERPT_S)
    if "vocalmix" in needed:
        manifest = json.loads(vocalmix.MANIFEST.read_text())
        hold = sorted(a["id"] for a in manifest["acappellas"] if a["split"] == "holdout")
        _expect("vocalmix.holdout_vocals", sorted(ds["vocalmix"]["holdout_vocals"]), hold)
        _expect("vocalmix.pairs_per_vocal", ds["vocalmix"]["pairs_per_vocal"], vocalmix.PAIRS_PER_VOCAL)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=sorted(DATASETS))
    ap.add_argument("--split", required=True, choices=["dev", "holdout"])
    ap.add_argument("--separator", required=True)
    ap.add_argument("--out", type=Path, default=BENCH / "results")
    ap.add_argument("--frozen-config", type=Path)
    ap.add_argument("--save-audio", action="store_true", help="write estimates under .cache/outputs for listening")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--allow-dirty", action="store_true",
                    help="permit a holdout run with uncommitted harness changes (recorded in the result)")
    args = ap.parse_args(argv)

    frozen_sha = None
    dirty, rev = git_dirty(), git_rev()
    if args.split == "holdout":
        if not args.frozen_config or not args.frozen_config.exists():
            ap.error("holdout runs require --frozen-config (fixed before scoring)")
        cfg = json.loads(args.frozen_config.read_text())
        try:
            check_frozen(cfg, args.dataset, create(args.separator))
        except ValueError as e:
            ap.error(str(e))
        if (dirty is None or rev == "unknown") and not args.allow_dirty:
            ap.error("cannot determine git status of the harness (not a git checkout, or git failed); "
                     "pass --allow-dirty to run without verified source identity")
        if dirty and not args.allow_dirty:
            ap.error(f"uncommitted changes under {SOURCE_PATHS}; commit them or pass --allow-dirty")
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
        results.append({"item": item.id, "input_sha256": item_digest(item), "license": item.license, "duration_s": dur,
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
        "frozen_config_sha256": frozen_sha, "git_rev": rev, "git_dirty": dirty,
        "allow_dirty": bool(args.allow_dirty),
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
