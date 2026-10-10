#!/usr/bin/env bash
# Run every dataset x separator sequentially for one split (dev | holdout).
set -euo pipefail
cd "$(dirname "$0")/.."
split="${1:?usage: run_all.sh dev|holdout}"
extra=()
[[ "$split" == holdout ]] && extra=(--frozen-config config/frozen.json)
seps=(baseline.mixture baseline.hpss mdx.Kim_Vocal_2 mdx.UVR-MDX-NET-Inst_HQ_3 demucs.htdemucs demucs.htdemucs_ft)
for ds in procedural babyslakh vocalmix; do
  for sep in "${seps[@]}"; do
    .venv/bin/python -m stemforge_bench.run --dataset "$ds" --split "$split" --separator "$sep" "${extra[@]}"
  done
done
.venv/bin/python scripts/summarize.py > /dev/null
