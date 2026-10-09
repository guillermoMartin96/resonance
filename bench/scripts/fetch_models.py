"""Download MDX-Net ONNX weights + UVR parameter table into .cache/models/mdx and verify.

    python scripts/fetch_models.py
Weights licence is UNSTATED upstream (TRvlvr/model_repo has no LICENSE file); they are
fetched for local evaluation only and never committed or redistributed.
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))
from stemforge_bench.separators.mdx_onnx import DOWNLOAD_URL, MODEL_DIR, PARAMS_URL  # noqa: E402

MODELS = {  # sha256 observed on 2026-10-09
    "Kim_Vocal_2.onnx": "ce74ef3b6a6024ce44211a07be9cf8bc6d87728cc852a68ab34eb8e58cde9c8b",
    "UVR-MDX-NET-Inst_HQ_3.onnx": "317554b07fe1ea5279a77f2b1520a41ea4b93432560c4ffd08792c30fddf9adc",
}


def fetch(url: str, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "stemforge-bench/0.0.1 (research)"})
    with urllib.request.urlopen(req, timeout=300) as r:
        dest.write_bytes(r.read())


def main() -> int:
    fetch(PARAMS_URL, MODEL_DIR / "model_data.json")
    for name, sha in MODELS.items():
        dest = MODEL_DIR / name
        fetch(DOWNLOAD_URL.format(name=name), dest)
        got = hashlib.sha256(dest.read_bytes()).hexdigest()
        if got != sha:
            print(f"sha256 mismatch for {name}: {got}", file=sys.stderr)
            return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
