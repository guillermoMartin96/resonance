# M0 / R2 — Separator evaluation

Date: 2026-10-09 · Machine: Intel i9-9880H, 32 GB, macOS 26.2, CPU only (`M0-environment.md`).
Method: `BENCHMARK_PROTOCOL.md`. Raw results: `bench/results/*.json`; generated tables: `bench/results/SUMMARY.md`.

## 1. Candidates and primary-source facts

| | **Demucs v4 (htdemucs / htdemucs_ft)** | **MDX-Net, UVR-trained (Kim_Vocal_2, Inst_HQ_3)** | Open-Unmix (not benchmarked) | HPSS baseline |
|---|---|---|---|---|
| Implementation | `demucs` 4.1.0 (PyPI, 2026-07-11), github.com/adefossez/demucs | our ONNX Runtime + numpy re-implementation of the UVR / python-audio-separator inference loop (`mdx_onnx.py`) | `openunmix` (sigsep) | scipy, in-repo |
| Code licence | MIT | MIT (UVR GUI, python-audio-separator) | MIT | project |
| **Weights licence** | **Unstated.** HF repos `adefossez/HTDemucs*` carry no licence tag; README states MIT for code only | **Unstated.** `TRvlvr/model_repo` has no LICENSE; UVR README only asks for credit | `umxl`: **CC BY-NC-SA 4.0** (non-commercial); `umxhq`/`umx`: unstated | none needed |
| Training data | MUSDB18-HQ (academic-use only) + ~800 undisclosed songs | undisclosed (UVR community training) | `umxl`: private stems; `umxhq`: MUSDB18-HQ | none |
| Maintenance | `facebookresearch/demucs` **archived 2025-01-01**; fork by original author is "officially maintained" but "not actively working on Demucs anymore" (bug fixes only). v4.1.0 moved weights to HF + safetensors | UVR GUI active (dev update Oct 2026); python-audio-separator active (0.47.0, 2026-08-27) but **not installable on Intel Mac**; model repo last release 2022 | last news entry 2024-04 | n/a |
| Stems | vocals, drums, bass, other (6-stem variant adds guitar/piano) | 2: vocals + instrumental (secondary derived as mix − primary × compensate) | 4 | drums/bass/other (crude) |
| Install on this machine | `pip install demucs` **fails** (sphn needs Rust); works with `--no-deps` + explicit deps. torch 2.2.2 ceiling | onnxruntime 1.23.2 wheel installs cleanly; no torch needed for our adapter | not attempted (would reuse torch 2.2.2) | trivial |
| Runtime footprint | torch 585 MB + sympy/networkx 91 MB; weights 177 MB (htdemucs, incl. sidecars) / 678 MB (ft) | onnxruntime 74 MB; weights 64 MB per model | – | – |
| CPU support | yes (documented) | yes (CPU EP; CoreML EP present, untested) | yes | yes |

Open-Unmix was screened out before benchmarking: its best weights are explicitly non-commercial, the rest are trained on academic-only data with unstated weight licences, and published MUSDB results trail both Demucs v4 and MDX-Net. BS-RoFormer / Mel-RoFormer models (current state of the art, run via python-audio-separator) were not benchmarked because that package can't be installed here; they are a candidate for a Linux-container worker (DR-0003 option B).

## 2. Implementation verification
- **numpy STFT/ISTFT** in the MDX adapter matches `torch.stft`/`torch.istft` to 1e-8 (`tests/test_separators.py::test_numpy_stft_matches_torch`).
- **MDX parity vs reference** (audio-separator 0.21.2, throwaway venv, same input): Inst_HQ_3 primary stem SI-SDR **47.7 dB** vs reference (gain 1.022 = UVR's `compensate`), so the adapter reproduces the reference algorithm. Kim_Vocal_2's instrumental differed (−3.9 dB) because of a **reference bug**: 0.21.2 normalises the primary stem *in place* (amplification threshold 0.6) before subtracting it from the mix, so a near-silent vocal estimate is boosted and the "instrumental" gets corrupted (confirmed: reference instrumental = mix − amplified vocals at 73.6 dB). Our adapter does not have this bug.
- Contract tests run every adapter, including real weights, through `validate_output` (role completeness, shape, finiteness, input not mutated).

## 3. Results — dev split (used for sanity and fixture fixes only; nothing was tuned on it)

Median over items, global SDR in dB (higher is better). Full metrics, including SI-SDR/SIR/SAR, are in `bench/results/SUMMARY.md`.

**vocalmix / dev** (4 items: real vocals over BabySlakh, 16 kHz)

| separator | vocals | accompaniment | drums | bass | other |
|---|---|---|---|---|---|
| baseline.mixture | ≈0 | ≈0 | – | – | – |
| baseline.hpss | – | – | −2.65 | 1.70 | 1.44 |
| demucs.htdemucs | 11.26 | 9.93 | 7.61 | 7.78 | 5.76 |
| demucs.htdemucs_ft | 11.10 | 8.92 | 8.29 | 8.74 | 5.03 |
| mdx.Kim_Vocal_2 | 13.09 | 13.43 | – | – | – |
| mdx.UVR-MDX-NET-Inst_HQ_3 | **13.27** | **13.56** | – | – | – |

**babyslakh / dev** (5 items, no vocals)

| separator | drums | bass | other | vocal-stem leakage (dB re. mix, lower = better) |
|---|---|---|---|---|
| baseline.hpss | 2.84 | 1.68 | 5.00 | – |
| demucs.htdemucs | 10.21 | 8.15 | 11.19 | **−49.0** |
| demucs.htdemucs_ft | **11.51** | **8.81** | **11.35** | −52.0 |
| mdx.Kim_Vocal_2 | – | – | – | −34.7 |
| mdx.UVR-MDX-NET-Inst_HQ_3 | – | – | – | −33.6 |

**procedural / dev**: Demucs drums 16.8 dB (ft 18.4), bass 5.9 (ft 8.8). Every ML model returned near-silence for the formant-synth "vocals" (SDR ≈ 0), which makes the procedural vocal stem **invalid as a vocal test** (see protocol). Its other stem was mostly misassigned (≈ −1 dB) by every engine.

## 4. Results — holdout split (scored once, frozen config `cb98142e…`, committed in `e26d6d2` before any real-audio run)

Median (mean) over items, dB. 144 item-scores across 18 runs; every holdout result JSON records the frozen-config sha256.
BabySlakh holdout has 14 items, not 15: Track00017 ships without its bass stem file (`S04.wav`), so the loader's existing rule (drums, bass and other must all be present) excluded it.

**vocalmix / holdout**: 6 items, 3 vocal recordings (solo, two choirs) whose singers don't appear in dev

| separator | vocals SDR | vocals SIR (bleed) | vocals SAR (artifacts) | accompaniment SDR | drums | bass | other |
|---|---|---|---|---|---|---|---|
| baseline.hpss | – | – | – | – | −3.31 | 0.70 | 1.14 |
| demucs.htdemucs | 10.31 (10.57) | 19.0 | 10.7 | 10.31 | 12.04 | 4.88 | 5.80 |
| demucs.htdemucs_ft | 10.51 (10.37) | 21.6 | 10.7 | 9.68 | **12.24** | 4.44 | **5.93** |
| mdx.Kim_Vocal_2 | **11.92 (13.31)** | **22.9** | **12.0** | **12.02** | – | – | – |
| mdx.UVR-MDX-NET-Inst_HQ_3 | 11.72 (12.80) | 22.8 | 11.8 | 11.82 | – | – | – |

**babyslakh / holdout**: 14 items, instrumental only

| separator | drums | bass | other | "accompaniment" kept intact (SDR, higher = better) | false-vocal leakage (dB re. mix, lower = better) |
|---|---|---|---|---|---|
| baseline.hpss | 2.86 | 1.49 | 5.85 | – | – |
| demucs.htdemucs | 9.92 | 5.26 | 10.23 | 30.35 | −46.7 |
| demucs.htdemucs_ft | **11.09** | **5.28** | 10.19 | 21.53 | **−48.0** |
| mdx.Kim_Vocal_2 | – | – | – | **40.66** | −41.6 |
| mdx.UVR-MDX-NET-Inst_HQ_3 | – | – | – | 26.83 | **−27.9** (worst: Track00012 instrumental only 7.5 dB) |

**procedural / holdout**: same pattern as dev. Demucs drums 15.6 dB (ft 17.7); every model treats the synthetic vowels as silence (vocal SDR ≈ 0), as expected.

### Speed and memory (3-minute 44.1 kHz stereo, fresh process each, `results/perf__180s.json`)

| separator | load s | separate s | RTF | peak RSS |
|---|---|---|---|---|
| baseline.hpss | 0.0 | 14.9 | 0.08 | 2.4 GB |
| demucs.htdemucs | 3.0 | 109.6 | **0.61** | **3.3 GB** |
| demucs.htdemucs_ft | 5.0 | 452.0 | 2.51 | 3.8 GB |
| mdx.Kim_Vocal_2 | 0.4 | 119.5 | 0.66 | 4.0 GB |
| mdx.UVR-MDX-NET-Inst_HQ_3 | 0.4 | 115.0 | 0.64 | 4.4 GB |

Per-item RTF on 30 s clips is higher (MDX ≈ 0.8, Demucs ≈ 0.7) because of fixed chunk padding; use the probe for planning. MDX peak RSS reflects our unoptimised float64 adapter and/or the ONNX Runtime memory arena, not the 64 MB model. That's an optimisation item, not a property of the model.

## 5. Interpretation

1. **Vocals**: MDX-Net vocal models beat Demucs v4 by about **+1.4–1.6 dB median SDR** on held-out real vocals, with less bleed (SIR +3–4 dB) and fewer artifacts (SAR +1.2 dB). The dev split showed the same ordering (+1.8–2.0 dB). With 6 items this is consistent but not conclusive.
2. **Drums / bass / other**: only Demucs provides them. Against the zero-weights HPSS baseline it wins by ~7 dB on drums, ~4 dB on bass and ~4 dB on other. Bass is the weakest stem (≈5 dB holdout). `htdemucs_ft` adds about +1.2 dB on BabySlakh drums at **4× the CPU time**; elsewhere it's a tie.
3. **Sampler-relevant failure mode (false vocals)**: on instrumental-only material, `Inst_HQ_3` pulls melodic instruments into "vocals" (leakage −27.9 dB, one track losing much of its instrumental: 7.5 dB). `Kim_Vocal_2` and Demucs largely leave instrumentals alone. For a tool whose users chop instrumentals, that matters more than a 0.2 dB vocal difference, so **Kim_Vocal_2 ranks above Inst_HQ_3**.
4. **Speed**: htdemucs and a single MDX model cost about the same on this CPU (RTF ≈ 0.6–0.7, so a 3-minute song takes about 2 minutes). Running both (4 stems + better vocals) costs about 2× that.
5. **Licensing is the blocker, not quality.** Neither family states a licence for its weights, and both were trained at least partly on data whose terms (academic-only MUSDB18, undisclosed sets) give no assurance for commercial output. Code licences (MIT) don't settle this.
6. **Not measured**: full-band (> 8 kHz) artifacts, real full productions in the target genres, subjective listening. See limitations.

## 6. Limitations
- Small n (holdout: 6 vocal mixes, 14 instrumental excerpts). Treat differences < ~1 dB as ties.
- 16 kHz material hides cymbal/hi-hat artifacts, which are the most audible Demucs/MDX failure modes in practice.
- BabySlakh is MIDI rendered with sample libraries; the vocal mixes are musically unrelated; 2 of 3 holdout vocals are choirs.
- SIR/SAR come from an instantaneous projection (no FIR allowance), so they're comparable across engines here but not with published BSS-Eval numbers.
- No blind listening was done (the rubric is in the protocol). Numbers aren't a substitute for it.
- Single machine, CPU only, default parameters, no tuning (deliberate).
- **Demucs run-to-run variation (found in independent review, M0-04).** The original Demucs numbers came from one *unseeded* random shift offset. A seeded re-run moved the per-stem medians by ≤ 0.25 dB, far below the gaps the conclusions rest on. The exception is BabySlakh **bass, htdemucs vs htdemucs_ft, which is a tie within noise**. Demucs is now bit-repeatable. Evidence: `docs/reviews/M0-review.md`, `bench/results/rerun-2026-10-09/`.
