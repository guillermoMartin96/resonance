# DR-0001 — Separation engine selection

Status: **APPROVED (provisional) — 2026-10-09, by the owner/technical lead.** Option C, under the conditions in *Decision record* below. No engine has been integrated into product code yet.

## Decision
Choose the initial separation backend(s) for M1, given legal use, fidelity, runtime and developer compatibility.

## Evidence
- R1 environment: `docs/research/M0-environment.md` (Intel macOS, CPU-only, torch 2.2.2 / onnxruntime 1.23.2 ceilings)
- R2 licence/maintenance matrix + R4 measurements: `docs/research/M0-separator-evaluation.md`
- R3 protocol and data: `docs/research/BENCHMARK_PROTOCOL.md`, `bench/data/manifest.json`
- Raw results: `bench/results/` (holdout tied to frozen config sha256 `cb98142e…`, commit `e26d6d2`)
- Proof record: `docs/proof/M0-proof.md`

### Holdout summary (median global SDR, dB)
| | vocals (real) | drums | bass | other | false-vocal leak on instrumentals | RTF (3 min, CPU) | peak RAM |
|---|---|---|---|---|---|---|---|
| HPSS baseline | – | 2.9 | 1.5 | 5.9 | – | 0.08 | 2.4 GB |
| **Demucs htdemucs** | 10.3 | 9.9 | 5.3 | 10.2 | −46.7 dB | **0.61** | 3.3 GB |
| Demucs htdemucs_ft | 10.5 | 11.1 | 5.3 | 10.2 | −48.0 dB | 2.51 | 3.8 GB |
| **MDX Kim_Vocal_2** | **11.9** | – | – | – | −41.6 dB | 0.66 | 4.0 GB* |
| MDX Inst_HQ_3 | 11.7 | – | – | – | −27.9 dB (bad) | 0.64 | 4.4 GB* |

\* adapter not memory-optimised. Drums/bass/other figures are from BabySlakh (16 kHz), vocals from the 6-item vocalmix holdout.

## Options
A. **Demucs `htdemucs` only.** One engine, 4 stems (drums/bass/other are what samplers need most), fastest ML option, best-documented. Weights licence unstated; torch 2.2.2 pinned on this machine; upstream in bug-fix-only mode.
B. **MDX `Kim_Vocal_2` only.** Best vocals and light runtime (onnxruntime, no torch), but only vocals/instrumental, which doesn't serve drum/bass sampling. Weights licence unstated; provenance of training data least documented.
C. **A + B behind the adapter registry (recommended).** Demucs `htdemucs` is the default 4-stem engine; `Kim_Vocal_2` is an optional "vocal focus" engine the user can run on the same asset. Both keep `baseline.hpss`/`baseline.mixture` as zero-licence fallbacks.
D. **Baselines only for M1** (playback/provenance pipeline with `baseline.mixture`/`hpss`), deferring any ML weights until the licence questions are answered. Lowest legal risk; poor separation quality.
E. Re-evaluate RoFormer-family models in a Linux container first (DR-0003 B). More setup, likely better quality, same licence questions.

## Recommendation
**Option C for local, non-commercial development and evaluation only**, with these conditions:
1. Keep the adapter layer and registry exactly as validated in M0. No engine-specific types leak into API/UI.
2. Surface `weights_license: unstated` in the UI and in every provenance manifest. Don't enable commercial export on the basis of these weights.
3. Make M1's first integrated engine `htdemucs` (4 stems). `Kim_Vocal_2` follows as a second adapter in the same release, or the next one.
4. Don't use `htdemucs_ft` as the default (4× slower for ≈ +1 dB on drums). It can be offered later as a "high quality, slow" option.
5. Don't use `Inst_HQ_3` (pulls melodic instruments into vocals on instrumental material).

If commercial distribution of outputs is in scope (PRODUCT.md open question), **approve D for anything shipped** until a weights licence is obtained in writing, or until a model trained on licensed data is found. That's a legal question for the owner/counsel, not something the benchmark can settle.

## Limitations of this evidence
Small holdout (6 vocal mixes, 14 instrumental excerpts); 16 kHz material under-measures high-frequency artifacts; no blind listening yet; single CPU machine. See evaluation §6. Recommended before final sign-off: run the blind listening rubric on `vocalmix` dev outputs (≈ 20 min of the owner's time), and add 5–10 full-band, genre-relevant items (DR-0002).

## Reversibility
Fully reversible: engines are registry entries behind one protocol, weights aren't committed, and switching engines changes only `separator_id`. Irreversible only if outputs are distributed commercially under an unverified weights licence.

## Decision record (2026-10-09)
**Approved:** Demucs `htdemucs` as the *provisional* four-stem engine; MDX `Kim_Vocal_2` as the *optional* enhanced-vocal engine (option C).

Binding conditions:
1. **Adapter interface preserved.** Both engines stay behind the `Separator` protocol (`bench/stemforge_bench/separators/base.py`) and its M1 successor; no engine-specific types in API/UI/storage.
2. **No-ML baseline is the M1 default.** The M1 pipeline ships with `baseline.mixture` / `baseline.hpss` selected by default; ML engines are opt-in.
3. **Enhanced vocals optional.** `Kim_Vocal_2` is never required for any workflow.
4. **Reproducibility.** Pinned package versions, weight sha256 checksums verified before use, frozen configuration, and provenance metadata (engine, version, model, weights sha256, params, input hash) on every output.
5. **Non-commercial use only for ML weights.** Both weight sets have *unstated* licences. Use is limited to non-commercial research and prototyping until commercial rights are verified in writing. Commercial export stays disabled for ML-derived outputs.
6. **Code licence ≠ weight rights.** MIT code licences (demucs, audio-separator) say nothing about the weights or the training data. No document or UI may imply otherwise.
7. **Replaceable.** Either engine can be swapped by changing a registry entry and `separator_id`; nothing may depend on a specific engine's internals.

Not decided here: whether commercial export is in product scope (`docs/PRODUCT.md` open question). Until it is, the restriction in condition 5 applies.

Still open evidence (does not block the provisional approval, does block calling the choice *final*): blind listening results (owner) and the expanded full-band corpus (DR-0002).
