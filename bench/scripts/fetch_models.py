"""Download MDX-Net ONNX weights + UVR parameter table into .cache/models/mdx and verify.

    python scripts/fetch_models.py
Weights licence is UNSTATED upstream (TRvlvr/model_repo has no LICENSE file); they are
fetched for local evaluation only and never committed or redistributed.
Every file is downloaded to a temporary sibling, checked against its pinned sha256
and only then moved into place; a cached file with the wrong hash is re-downloaded.
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))
from stemforge_bench.separators.mdx_onnx import (  # noqa: E402
    DOWNLOAD_URL, MODEL_DIR, MODEL_SHA256, PARAMS_SHA256, PARAMS_URL, sha256_file)


class ChecksumError(RuntimeError):
    pass


def fetch(url: str, dest: Path, sha256: str) -> None:
    if dest.exists():
        if sha256_file(dest) == sha256:
            return
        print(f"{dest.name}: cached file has the wrong sha256, re-downloading", file=sys.stderr)
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "stemforge-bench/0.0.1 (research)"})
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                h.update(chunk)
                f.write(chunk)
        if h.hexdigest() != sha256:
            raise ChecksumError(f"sha256 mismatch for {url}: expected {sha256}, got {h.hexdigest()}")
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    try:
        fetch(PARAMS_URL, MODEL_DIR / "model_data.json", PARAMS_SHA256)
        for name, sha in MODEL_SHA256.items():
            fetch(DOWNLOAD_URL.format(name=name), MODEL_DIR / name, sha)
    except ChecksumError as e:
        print(e, file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
