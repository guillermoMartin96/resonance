# Separation benchmark protocol (R3)

Harness: `bench/` (`stemforge_bench` package). Reproduce with the commands in `bench/README.md`.

## Principles
1. **Legally usable audio only.** No commercial releases, no MUSDB18/MedleyDB/MoisesDB (academic/non-commercial terms), no streaming capture. Source audio is downloaded by `bench/scripts/fetch_data.py` into `bench/.cache/` (git-ignored) and verified by checksum; **no audio is committed**.
2. **Exact ground truth.** Every mixture is the exact sum of its reference stems (same gain applied to all stems), so metrics measure the separator, not a mastering chain.
3. **Dev / holdout discipline.** Splits are fixed in code and in `bench/data/manifest.json` before any model is run on holdout. Anything that can be tuned (fixture design, adapter parameters, excerpt selection, chosen models) is tuned on **dev only**. Holdout runs require `--frozen-config bench/config/frozen.json`; the file's sha256 is stored in every holdout result. Holdout is scored once; if the config changes afterwards, the change and the reason are recorded and the old numbers kept.
4. **No model chosen by popularity.** Candidates are scored on the same items, same metrics, same machine, one process per engine.

## Datasets

| Dataset | What | License | Dev | Holdout | Stems with ground truth |
|---|---|---|---|---|---|
| `procedural` | Deterministic synthetic multitracks (kick/snare/hat synthesis, saw bass, additive keys, formant-synthesised vowels), 44.1 kHz stereo, 24 s, each stem has one silent bar | CC0 (generated) | seeds 0–3 | seeds 1000–1003 | vocals*, drums, bass, other |
| `babyslakh` | First 20 tracks of Slakh2100: Lakh-MIDI rendered with sample-based virtual instruments (i.e. real recorded instrument samples), 16 kHz mono; deterministic 30 s excerpt per track | CC BY 4.0 | Track00001–05 | Track00006–20 | drums, bass, other (no vocals) |
| `vocalmix` | Real unaccompanied vocal recordings from Wikimedia Commons over BabySlakh accompaniment from the same split; 16 kHz mono, 30 s, vocal level matched to accompaniment (0 dB) | vocals CC0 / public domain / CC BY-SA 4.0; accompaniment CC BY 4.0 | 2 vocals × 2 accompaniments | 3 vocals × 2 accompaniments (singers disjoint from dev) | vocals, drums, bass, other |

\* **The procedural "vocals" are not a valid vocal test.** On dev, every ML model returned near-silence for them (vocal SDR ≈ 0 dB, i.e. estimate ≈ 0). The models do not hear formant-synthesised vowels as singing. Procedural results are used for pipeline/regression checks and drum/bass sanity only.

Attribution strings for every source file live in `bench/data/manifest.json` and are carried into each result item's `license` field.

Known dataset limitations (affect how far results generalise):
- 16 kHz material is band-limited to 8 kHz; models run at 44.1 kHz on upsampled input. High-frequency artifacts (hi-hat "swirl", cymbal smearing) are therefore **under-measured**.
- Slakh instruments are sample-based MIDI renders: no live-room bleed, no mastering, no human timing. Real recordings are harder.
- `vocalmix` vocals and accompaniment are musically unrelated (key/tempo). Two of five vocal recordings are choirs.
- Sample sizes are small (dev 4–5 items, holdout 6–15 items per dataset). Differences under ~1 dB should be treated as ties.

## Separators under test
Registered in `bench/stemforge_bench/separators/__init__.py`, all behind the same `Separator` protocol:

| id | Engine | Stems |
|---|---|---|
| `baseline.mixture` | identity (each stem = mixture) — SDR floor and pipeline pass-through | all |
| `baseline.hpss` | median-filter harmonic/percussive split + 180 Hz low-pass for bass; zero weights, zero licence questions | drums, bass, other |
| `demucs.htdemucs` | Demucs v4 Hybrid Transformer, default model | vocals, drums, bass, other (+ derived accompaniment) |
| `demucs.htdemucs_ft` | fine-tuned bag of 4 htdemucs models (~4× slower) | same |
| `mdx.Kim_Vocal_2` | UVR MDX-Net vocal model via our ONNX Runtime adapter | vocals, accompaniment |
| `mdx.UVR-MDX-NET-Inst_HQ_3` | UVR MDX-Net instrumental model via our ONNX Runtime adapter | vocals, accompaniment |

Parameters are the engines' documented defaults (Demucs: shifts=1, overlap=0.25, seed 0; MDX: hop 1024, segment 256, overlap 0.25, denoise off) and are recorded in each result's `separator.params`.

## Metrics (`bench/stemforge_bench/metrics.py`)

| Metric | Meaning | Caveat |
|---|---|---|
| **SDR** | global SDR as used by the MDX'21 challenge / Demucs v4 paper: `10·log10(Σs² / Σ(s−ŝ)²)` | not the filtered BSS-Eval v4 SDR; not directly comparable with older MUSDB tables |
| **SI-SDR** | scale-invariant SDR | ignores gain errors |
| **SIR — "bleed"** | least-squares projection of the estimate on all reference stems; target energy vs. other-stem energy | instantaneous projection (no FIR allowance), so read as relative |
| **SAR — "artifacts"** | projected (explained) energy vs. residual not explained by any source | phase smearing and filtering count as artifacts |
| **silent-leak** | in 1 s windows where the target is silent but the mix is not: estimate energy relative to mixture energy, dB | the sampler's view: "what do I hear when I chop a region where the instrument isn't playing?" |
| **RTF** | processing seconds / audio seconds, single process, CPU | includes resampling; excludes model load |
| **load s / peak RSS** | model load time; process peak resident memory (macOS `ru_maxrss`) | peak RSS includes interpreter, runtime and data |

Installation complexity is assessed from the actual install log (dependency failures, workarounds, disk footprint) — see `docs/research/M0-environment.md`.

## Performance probe
`bench/scripts/perf_probe.py --seconds 180` writes a 3-minute deterministic CC0 mixture to disk once, then runs each separator in a **fresh process** (read WAV → load → separate) and records wall time and peak RSS. Benchmarks are run sequentially, never concurrently, to avoid CPU contention.

## Blind listening rubric (R3 subjective; packet ready, owner results pending; step-by-step: `LISTENING_TEST.md`)
Objective metrics miss what samplers care about (transients, "underwater" phasiness, vocal breaths). Before DR-0001 is approved, a human should run:
1. `bench/.venv/bin/python -m stemforge_bench.run --dataset vocalmix --split dev --separator <id> --save-audio` for each candidate (writes to `bench/.cache/outputs/`).
2. `bench/scripts/make_listening_packet.py` copies outputs into `bench/.cache/listening/` with randomised labels (A/B/C…), loudness-matched per item, plus a blank `ratings.csv`; the key goes to `bench/.cache/listening_keys/` (outside the packet).
3. For each item and stem, rate 1–5 on: **isolation** (how little of other instruments is audible), **integrity** (target sounds intact: transients, tails, breaths), **artifacts** (phasiness, warbling, metallic noise; 5 = none), **usability** ("would I sample this region?" yes/no). Note timestamps of failures.
4. Unblind with the key and record the table in `docs/research/M0-separator-evaluation.md`.

No subjective listening was done by the agent; nothing in the evaluation should be read as a listening verdict.
