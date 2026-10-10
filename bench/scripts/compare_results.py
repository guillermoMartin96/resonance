"""Compare re-run result JSONs against the committed originals (reproducibility check).

    python scripts/compare_results.py results/rerun-2026-10-09 [--base results]
For each re-run file, matched by name in --base: per role, the median SDR of each run
over its own valid scores, the delta, and the largest per-item |SDR difference|.
Exit 1 if the item set, the role set, or any item's score validity (None vs number)
differs, or if the base file is missing.
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
    paths = sorted(args.rerun.glob("*__*__*.json"))
    if not paths:
        print(f"no result files in {args.rerun}")
        return 1
    for path in paths:
        if not (args.base / path.name).exists():
            print(f"| {path.stem} | NO BASE FILE | | | | |")
            status = 1
            continue
        base, new = json.loads((args.base / path.name).read_text()), json.loads(path.read_text())
        b_items = {it["item"]: it for it in base["items"]}
        n_items = {it["item"]: it for it in new["items"]}
        if set(b_items) != set(n_items):
            print(f"| {path.stem} | ITEM SET DIFFERS | | | | |")
            status = 1
            continue
        roles = {i: set(it["metrics"]) for i, it in n_items.items()}
        if any(roles[i] != set(b_items[i]["metrics"]) for i in n_items):
            print(f"| {path.stem} | ROLE SET DIFFERS | | | | |")
            status = 1
            continue
        for role in sorted(set().union(*roles.values())):
            pairs = [(b_items[i]["metrics"][role]["sdr"], n_items[i]["metrics"][role]["sdr"]) for i in sorted(n_items)]
            changed = [i for i, (a, b) in zip(sorted(n_items), pairs) if (a is None) != (b is None)]
            if changed:
                print(f"| {path.stem} | {role}: SDR VALIDITY DIFFERS for {', '.join(changed)} | | | | |")
                status = 1
                continue
            valid = [(a, b) for a, b in pairs if a is not None]
            if not valid:
                continue
            mb, mn = st.median(a for a, _ in valid), st.median(b for _, b in valid)
            worst = max(abs(a - b) for a, b in valid)
            print(f"| {path.stem} | {role} | {mb:.3f} | {mn:.3f} | {mn - mb:+.3f} | {worst:.3f} |")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
