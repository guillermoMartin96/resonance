"""Download benchmark audio listed in data/manifest.json into .cache/ and pin checksums.

    python scripts/fetch_data.py            # download + verify
Checksums for a cappellas are recorded in data/checksums.json on first download and
verified afterwards, so later runs detect upstream changes.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
CACHE = BENCH / ".cache"
MANIFEST = json.loads((BENCH / "data" / "manifest.json").read_text())
CHECKSUMS = BENCH / "data" / "checksums.json"


def digest(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "stemforge-bench/0.0.1 (research)"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            wait = int(e.headers.get("Retry-After") or 30 * (attempt + 1))
            print(f"429 from server, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
    tmp.rename(dest)
    time.sleep(2)  # be polite to upstream hosts


def main() -> int:
    bs = MANIFEST["babyslakh"]
    archive = CACHE / "babyslakh" / "babyslakh_16k.tar.gz"
    download(bs["url"], archive)
    if digest(archive, "md5") != bs["md5"]:
        print(f"md5 mismatch for {archive}", file=sys.stderr)
        return 1
    root = CACHE / "babyslakh"
    if not (root / "babyslakh_16k").exists():
        with tarfile.open(archive) as tar:
            tar.extractall(root, filter="data")  # rejects absolute paths / traversal
    sums = json.loads(CHECKSUMS.read_text()) if CHECKSUMS.exists() else {}
    for a in MANIFEST["acappellas"]:
        dest = CACHE / "acappellas" / (a["id"] + Path(a["url"]).suffix)
        download(a["url"], dest)
        if "sha1" in a and digest(dest, "sha1") != a["sha1"]:
            print(f"sha1 mismatch for {a['id']} (manifest pins the Wikimedia Commons sha1)", file=sys.stderr)
            return 1
        sha = digest(dest, "sha256")
        if a["id"] in sums and sums[a["id"]] != sha:
            print(f"sha256 changed for {a['id']}: {sums[a['id']]} -> {sha}", file=sys.stderr)
            return 1
        sums[a["id"]] = sha
    CHECKSUMS.write_text(json.dumps(sums, indent=2, sort_keys=True) + "\n")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
