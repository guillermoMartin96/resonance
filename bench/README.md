# StemForge separation benchmark (M0 research harness)

Research code, not product code. Compares source-separation engines behind one
provider-neutral `Separator` protocol on legally usable audio with exact ground truth.
Protocol and caveats: `docs/research/BENCHMARK_PROTOCOL.md`. Findings:
`docs/research/M0-separator-evaluation.md`.

## Setup (Intel macOS, CPU; see docs/research/M0-environment.md)
```bash
~/.local/bin/python3.12 -m venv bench/.venv
bench/.venv/bin/python -m pip install "torch==2.2.2" "onnxruntime==1.23.2" "numpy<2" \
  "soundfile==0.13.1" scipy pytest pyyaml einops huggingface-hub "julius>=0.2.3" \
  "lameenc>=1.2" safetensors tqdm
bench/.venv/bin/python -m pip install --no-deps "demucs==4.1.0"   # sphn has no Intel-Mac wheel
```
Exact versions: `requirements.lock.txt`. On other platforms a plain `pip install demucs==4.1.0` works.

## Data and weights (downloaded, never committed)
```bash
cd bench
.venv/bin/python scripts/fetch_data.py     # BabySlakh (CC BY 4.0, ~880 MB) + 5 Commons vocals; verifies md5/sha1
.venv/bin/python scripts/fetch_models.py   # MDX ONNX weights + UVR parameter table; verifies sha256
```
Demucs weights are fetched from Hugging Face (`adefossez/HTDemucs*`) on first use and hashed into every result.

## Run
```bash
cd bench
.venv/bin/python -m pytest -q                                   # unit + contract tests (incl. real-weight smoke tests)
.venv/bin/python -m stemforge_bench.run --dataset vocalmix --split dev --separator demucs.htdemucs [--save-audio]
.venv/bin/python -m stemforge_bench.run --dataset vocalmix --split holdout --separator demucs.htdemucs \
    --frozen-config config/frozen.json                          # holdout requires the frozen config
.venv/bin/python scripts/perf_probe.py --seconds 180            # RTF + peak RSS, fresh process per engine
.venv/bin/python scripts/summarize.py                           # -> results/SUMMARY.md
.venv/bin/python scripts/make_listening_packet.py --dataset vocalmix --role vocals   # blinded A/B packet
```
`scripts/run_all.sh dev|holdout` runs every dataset × separator sequentially.

## Layout
```
stemforge_bench/separators/   base.py (protocol), baselines.py, demucs_adapter.py, mdx_onnx.py, registry
stemforge_bench/datasets/     procedural.py (CC0 synth), slakh.py (BabySlakh), vocalmix.py (Commons vocals + BabySlakh)
stemforge_bench/metrics.py    SDR, SI-SDR, SIR/SAR projection, silent-target leakage
stemforge_bench/run.py        one separator × one dataset split -> results/*.json
data/manifest.json            sources, licences, attribution, split assignment, rejected sources
config/frozen.json            configuration fixed before holdout scoring
results/                      JSON results + SUMMARY.md (committed; small)
```
