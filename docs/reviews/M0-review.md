# Independent review — M0

**Milestone / branch / commit:** M0 · `feature/m0-research` · PR #1 (draft). Four review rounds: round 1 on `fe8a8f7`, round 2 on `3c020c6`, round 3 on `231b55b`, round 4 on `524cdda` (final reviewed code commit).

**Reviewer and scope:** OpenAI Codex CLI 0.162.0 (`codex exec -s read-only`, model `gpt-6.1-sol`, session `01a123ff-dd84-7aa2-8c25-b53ed80c706b`). It is independent of the authoring agent (Claude Code). The brief, with the seven owner-specified priorities, is in `docs/reviews/M0-review-handoff.md`. The reviewer inspected the code, git history, result JSONs and cached artefacts, and ran the test suite plus its own recomputation probes. It did not rely on the summaries. Its unedited output is in `docs/reviews/evidence/M0-codex-review-round1.md`.

## Findings and disposition (round 1)
Before fixing anything, the authoring agent re-checked each finding against the code: M0-02 against `demucs/hf.py` (`hf_hub_download` with no revision or checksum), M0-04 against `demucs/apply.py:245` (`random.randint`), and M0-05 against `perf_probe.py` (`/ 1e6` on every platform). All six were confirmed.

| ID | Sev. | Finding | Disposition | Fix and evidence |
|---|---|---|---|---|
| M0-01 | **High** | UVR parameter table (`model_data.json`) downloaded from a mutable `main` URL and used without a checksum; ONNX hashes verified only by the fetch script, not before use | **Fixed** | Table pinned to `TRvlvr/application_data@4621ca87…` and sha256 `1aca8f9b…`. That commit's content equals the table used for every M0 result (checked against all 21 historical revisions of the file). `MDXOnnxSeparator.load()` verifies the weights and the table *before* parsing or creating the ONNX session, and records the table hash and revision in `params`. Tests: `test_mdx_rejects_unpinned_or_tampered_weights`, `test_mdx_rejects_tampered_param_table`, `test_mdx_param_table_url_is_pinned_to_a_commit` |
| M0-02 | **High** | Demucs weights hashed after loading, not verified; unpinned HF revision; hashes taken from all cached snapshots; bag YAML not covered | **Fixed** | `demucs_adapter.PINNED`: HF commit plus sha256 for the YAML and every safetensors file of `htdemucs` and `htdemucs_ft`. `resolve_pinned_files()` downloads at the pinned revision and verifies every file before `load_safetensors_model`/`BagOfModels`. The pinned weight hashes are identical to `weights_sha256` in every committed Demucs result, so the published numbers trace to these exact files. Tests: `test_demucs_pins_revision_and_every_file`, `test_demucs_rejects_tampered_file_before_loading`, `test_demucs_unpinned_model_refused`, plus the real-weight contract test |
| M0-03 | Medium | Frozen config hash proves which file was passed, not that its settings ran; no input hashes | **Fixed** (going forward) | `run.check_frozen()` compares every frozen separator param with the adapter's params (unknown keys rejected) and the dataset settings with the code (procedural seeds/seconds, BabySlakh holdout range/excerpt, vocalmix holdout vocals/pairs). Holdout runs refuse a dirty `stemforge_bench/ config/ data/` tree unless `--allow-dirty` is passed, and record `git_dirty` and a per-item `input_sha256`. Tests: `test_committed_frozen_config_matches_code`, 6× `test_frozen_config_mismatch_rejected`, `test_item_digest_changes_with_content`. **Residual:** the committed original results predate this and have no input hashes. Five *dev* procedural results record `git_rev` `681ae1d` because they ran before the harness was first committed. No holdout result is affected (all 18 carry `e26d6d2`). |
| M0-04 | Medium | `torch.manual_seed` does not control Demucs shift offsets (`random.randint`), so outputs are not repeatable | **Fixed**; effect on published numbers quantified below | The adapter seeds Python's `random` per call and restores the caller's state. Test: `test_demucs_repeatable_with_same_seed` (bit-identical outputs, RNG state preserved). |
| M0-05 | Medium | `perf_probe` RSS ÷1e6 on Linux (KiB) → 1000× too small | **Fixed** | `stemforge_bench/platform_info.py` (platform logic isolated per DR-0003). `run.py` and `perf_probe` both use it. Tests: `test_rss_units`, `test_perf_probe_uses_platform_aware_rss`. macOS figures in the evidence are unaffected. |
| M0-06 | Low | Interrupted model download leaves a partial file that is never repaired | **Fixed** | `fetch_models.fetch()` streams to `.part`, verifies the sha256, `os.replace`s into place, and re-downloads cached files whose hash is wrong. Tests: `test_fetch_interrupted_leaves_no_destination`, `test_fetch_replaces_corrupt_cache_and_verifies` |

Found by the authoring agent while fixing (not by the reviewer): the first re-run attempt silently ran nothing (zsh word-splitting), and `compare_results.py` then exited 0 on an empty directory. Fixed in `bf24295` (empty → exit 1).

## Effect on the published evidence (M0-04 / reproducibility re-run)
After the fixes, 7 holdout configurations were re-run on a clean tree at `bf24295` with the unchanged frozen config (`cb98142e…`, `git_dirty: false`). Output went to `bench/results/rerun-2026-10-09/`; the original holdout JSONs were **not modified**. Command: `scripts/compare_results.py results/rerun-2026-10-09`.

| run | role | base median SDR | rerun median SDR | Δ median | max per-item abs Δ |
|---|---|---|---|---|---|
| babyslakh__holdout__baseline.hpss | drums | 2.862 | 2.862 | +0.000 | 0.000 |
| babyslakh__holdout__baseline.hpss | bass | 1.491 | 1.491 | +0.000 | 0.000 |
| babyslakh__holdout__baseline.hpss | other | 5.851 | 5.851 | +0.000 | 0.000 |
| babyslakh__holdout__demucs.htdemucs | drums | 9.919 | 9.910 | -0.009 | 0.415 |
| babyslakh__holdout__demucs.htdemucs | bass | 5.261 | 5.376 | +0.115 | 0.325 |
| babyslakh__holdout__demucs.htdemucs | other | 10.231 | 10.338 | +0.107 | 0.284 |
| babyslakh__holdout__demucs.htdemucs | accompaniment | 30.353 | 30.443 | +0.090 | 2.236 |
| babyslakh__holdout__demucs.htdemucs_ft | drums | 11.089 | 11.062 | -0.026 | 0.169 |
| babyslakh__holdout__demucs.htdemucs_ft | bass | 5.282 | 5.234 | -0.048 | 0.904 |
| babyslakh__holdout__demucs.htdemucs_ft | other | 10.191 | 10.417 | +0.227 | 0.384 |
| babyslakh__holdout__demucs.htdemucs_ft | accompaniment | 21.525 | 22.124 | +0.599 | 1.985 |
| vocalmix__holdout__demucs.htdemucs | vocals | 10.310 | 10.254 | -0.056 | 0.125 |
| vocalmix__holdout__demucs.htdemucs | drums | 12.038 | 11.939 | -0.099 | 0.163 |
| vocalmix__holdout__demucs.htdemucs | bass | 4.882 | 4.635 | -0.247 | 0.471 |
| vocalmix__holdout__demucs.htdemucs | other | 5.800 | 5.787 | -0.013 | 0.467 |
| vocalmix__holdout__demucs.htdemucs | accompaniment | 10.305 | 10.272 | -0.033 | 0.086 |
| vocalmix__holdout__demucs.htdemucs_ft | vocals | 10.509 | 10.554 | +0.044 | 0.064 |
| vocalmix__holdout__demucs.htdemucs_ft | drums | 12.241 | 12.184 | -0.057 | 0.448 |
| vocalmix__holdout__demucs.htdemucs_ft | bass | 4.440 | 4.522 | +0.082 | 0.326 |
| vocalmix__holdout__demucs.htdemucs_ft | other | 5.932 | 6.043 | +0.111 | 0.215 |
| vocalmix__holdout__demucs.htdemucs_ft | accompaniment | 9.684 | 9.412 | -0.272 | 0.590 |
| vocalmix__holdout__mdx.Kim_Vocal_2 | vocals | 11.919 | 11.919 | +0.000 | 0.000 |
| vocalmix__holdout__mdx.Kim_Vocal_2 | accompaniment | 12.025 | 12.025 | +0.000 | 0.000 |
| vocalmix__holdout__mdx.UVR-MDX-NET-Inst_HQ_3 | vocals | 11.724 | 11.724 | +0.000 | 0.000 |
| vocalmix__holdout__mdx.UVR-MDX-NET-Inst_HQ_3 | accompaniment | 11.819 | 11.819 | +0.000 | 0.000 |

Reading:
- **Deterministic engines reproduce exactly** (MDX ×2 and HPSS, Δ = 0.000 dB on every item). Inputs, metrics and the verified MDX artefacts are byte-stable since the freeze.
- **Demucs** originals were one unseeded draw of the shift offset. A seeded re-run moves the per-stem medians by ≤ 0.25 dB (≤ 0.6 dB on the 20–30 dB `accompaniment` sums, which no conclusion uses). The ranking gaps the decisions rely on are much larger: vocals Kim_Vocal_2 vs htdemucs ≈ 1.7 dB, drums htdemucs_ft vs htdemucs ≈ 1.15 dB, htdemucs vs HPSS ≥ 3.9 dB on every stem.
- **One comparison is within noise:** BabySlakh *bass*, htdemucs vs htdemucs_ft (originally 5.26 vs 5.28, re-run 5.38 vs 5.23). It is a tie. The evaluation already reported both as 5.3, and DR-0001 does not depend on it.
- Conclusion: DR-0001's ranking evidence stands. Going forward, Demucs results are repeatable bit for bit (`test_demucs_repeatable_with_same_seed`).

## Security and licence concerns
- No Critical/High security finding. The reviewer verified `.part` downloads for data, checksum before extraction, `tarfile` `filter="data"`, and argv-list subprocesses. All downloaded artefacts (dataset, vocals, ONNX weights, UVR table, Demucs YAML and weights) are now verified *before use*.
- Not established either way (reviewer "Not verified"): resistance of libsndfile/mpg123 to hostile files, and size/duration limits on downloads and decoding. In M0 every decoded file is checksum-pinned, so only known bytes are decoded. **For M1, which decodes user uploads, size/duration limits and decoding in a worker process are required.** Tracked as an M1 risk.
- Licences: the reviewer confirmed that DR-0001 keeps code licence and weight rights separate and restricts ML weights to non-commercial use. Independent *legal* verification of upstream licences was out of scope and was not done.

## Test coverage gaps (remaining)
- MDX parity against python-audio-separator rests on a one-off throwaway-venv comparison (47.7 / 73.6 dB). The reference cannot be installed on this machine (DR-0003), so there is no committed parity script. Recommended in M1: a Linux CI job that installs `audio-separator` and compares outputs on a fixed CC0 input.
- CI does not run the real-weight tests: it makes no weight downloads by design.

## Remediation commits
`e503145` (M0-01…06), `d8d9492` (compare script), `bf24295` (compare script false-pass), `b3b3994` (re-run evidence + docs), `524cdda` (round 3: M0-08, M0-03b), `bb18940` (round-2 Mediums).

## Round 2
Codex re-reviewed the fix diff `fe8a8f7..3c020c6` (session `01a12428-a2c4-7f43-80c3-5c33616e2f5d`; verbatim: `docs/reviews/evidence/M0-codex-review-round2.md`). It re-verified the cached artefact hashes, all 7 pinned Demucs files, Demucs loader parity with upstream `get_hf_model`, all 66 re-run input digests, exact metric equality on the 26 deterministic items, and that **all 18 original holdout JSONs are byte-identical** to round 1.

| ID | Round-2 status |
|---|---|
| M0-01 (High) | **Resolved** |
| M0-02 (High) | **Resolved** |
| M0-03 | Partially resolved → follow-ups M0-03a/b below |
| M0-04, M0-05, M0-06 | **Resolved** |

New findings in round 2. All are Medium and none blocking; all fixed in `bb18940`:

| ID | Sev. | Finding | Fix | Tests |
|---|---|---|---|---|
| M0-03a | Medium | Frozen config accepted an omitted param, unknown dataset keys, and a wrong `metrics_module` | Complete schema enforced (top-level, dataset and per-separator key sets must match exactly); `metrics_module` must equal the module actually imported. All 18 committed combinations still validate. | 5× `test_frozen_config_schema_is_complete` |
| M0-03b | Medium | Unknown git state (`None`) passed the dirty-tree gate | Holdout refuses unknown git state unless `--allow-dirty`, which is recorded in the result | `test_holdout_refuses_unknown_git_state` |
| M0-07 | Medium | `compare_results.py` dropped items whose score became `None` from both sides and reported a false match | Flags item-set, role-set and per-item validity changes and missing base files (exit 1); medians per run over its own valid scores. Re-running it on the committed re-run evidence still gives exit 0 with the same table. | 2× `test_compare_flags_validity_changes`, `test_compare_flags_role_set_change`, `test_compare_identical_passes` |

Round 2 verdict (Codex): **"Remaining blocking findings: none."**

## Round 3
Codex verified the round-2 fixes (session `01a1242c-e4ae-7943-9c35-5e3d101418d2`; verbatim: `evidence/M0-codex-review-round3.md`): **M0-03a Resolved, M0-07 Resolved, M0-03b Partially resolved**. It found one new issue:

| ID | Sev. | Finding | Fix (`524cdda`) |
|---|---|---|---|
| M0-08 | Medium | **Caused by the authoring agent.** When the new git-state test was first run against the unfixed code, `run.main()` executed and overwrote `results/procedural__holdout__baseline.mixture.json` with a 1-item probe, which `bb18940` then committed. That broke "original frozen benchmark unchanged". The real-audio results were not affected. | File restored byte for byte. The test now writes to `tmp_path`, stubs the dataset loader, and asserts the gate fires before any load. `results/HOLDOUT_SHA256.json` pins all 18 original holdout files and `test_original_holdout_results_untouched` enforces it. Every file in `bench/results/` that existed at `0ec5611` is byte-identical to it. |
| M0-03b (rest) | Medium | `git_rev == "unknown"` with a clean status still passed | Revision and status are both checked before loading; either unknown → refused unless `--allow-dirty`; the validated revision is the one recorded. Tests: 2× `test_holdout_refuses_unknown_git_state` |

## Round 4 (final)
Codex (session `01a12430-3316-7691-aa54-e51d91c16c4e`; verbatim: `evidence/M0-codex-review-round4.md`): **M0-03b Resolved, M0-08 Resolved; new findings: none; no Critical/High in `681ae1d..524cdda`. "Blocking findings: none. Fit to merge as provisional research: yes."** It noted that the hash guard pins the 18 holdout JSONs only; `SUMMARY.md`, dev and perf results were verified identical to `0ec5611` but are not guarded.

Final tally: 9 findings (2 High, 6 Medium, 1 Low). All fixed and independently confirmed resolved. None open.

Reviewer limitation, all rounds: the sandbox had no writable temp directory, so Codex could not execute the filesystem-dependent tests (listening packet, download atomicity, comparison, git gate). It covered their logic with in-memory probes. These tests pass locally (53/53) and in Linux CI.

## Remaining risks
See `docs/proof/M0-proof.md` → *Failures and limitations*, and the PR description.

## Merge recommendation
**Ready to merge as provisional M0 research, pending owner approval.** No Critical/High findings remain. Owner-side gates that stay open and do not block the merge: blind listening results (`docs/research/LISTENING_TEST.md`) and the DR-0002 expanded corpus (0 items). Neither may be reported as complete until done.

Carry-forward items for M1 (non-blocking):
- Size/duration limits and process-isolated decoding for user uploads.
- A committed MDX reference-parity check, as a Linux CI job.
- Commercial-use restriction on ML weights (DR-0001 condition 5).
