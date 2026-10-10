"""Compare re-run result JSONs against the committed originals (reproducibility check).

    python scripts/compare_results.py results/rerun-2026-10-09 [--base results]
For each re-run file, matched by name in --base: per role, the median SDR of both
runs, the delta, and the largest per-item |SDR difference|. Exit 1 if items differ.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rerun", type=Path)
    ap.add_argument("--base", type=Path, default=BENCH / "results")
    args = ap.parse_args()
    print("| run | role | base median SDR | rerun median SDR | Δ median | max per-item abs Δ |")
    print("|---|---|---|---|---|---|")
    status = 0
    for path in sorted(args.rerun.glob("*__*__*.json")):
        base, new = json.loads((args.base / path.name).read_text()), json.loads(path.read_text())
        b_items = {it["item"]: it for it in base["items"]}
        n_items = {it["item"]: it for it in new["items"]}
        if set(b_items) != set(n_items):
            print(f"| {path.stem} | ITEM SET DIFFERS | | | | |")
            status = 1
            continue
        for role in new["items"][0]["metrics"]:
            pairs = [(b_items[i]["metrics"][role]["sdr"], n_items[i]["metrics"][role]["sdr"]) for i in n_items]
            pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
            if not pairs:
                continue
            mb, mn = st.median(a for a, _ in pairs), st.median(b for _, b in pairs)
            worst = max(abs(a - b) for a, b in pairs)
            print(f"| {path.stem} | {role} | {mb:.3f} | {mn:.3f} | {mn - mb:+.3f} | {worst:.3f} |")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
