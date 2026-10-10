<!-- Verbatim final message of: codex exec -s read-only (codex-cli 0.162.0, model gpt-6.1-sol, session 01a1242c-e4ae-7943-9c35-5e3d101418d2), round-3 review of 231b55bed8770e1150d51bacb77dac30ba526ad5, 2026-10-09. Not edited. -->

## Commands run

Reviewed HEAD `231b55bed8770e1150d51bacb77dac30ba526ad5`. No files modified or downloads performed.

- `cat docs/reviews/M0-review-handoff.md docs/reviews/evidence/M0-codex-review-round2.md` — read review constraints and original findings.
- `git rev-parse HEAD`; `git status --short` — requested HEAD confirmed; clean worktree.
- `git show bb18940`; `git show --stat 231b55b` — inspected implementation fixes, tests, result replacement and subsequent documentation commit.
- `git diff 681ae1d..HEAD --stat`; `git diff 681ae1d..HEAD --name-only`; targeted `cat`, `nl`, and diffs — swept datasets, adapters, metrics, downloads, provenance, listening packets, CI, dependencies and research/decision documents.
- `git log` / `git show` for configuration, datasets and holdout results — checked split/configuration history and evidence preservation.
- `cd bench && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider -s` — **38 passed, 13 setup errors**; all errors arose from unavailable writable temporary directories.
- `cd bench && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/compare_results.py results/rerun-2026-10-09` — **exit 0**, all seven reruns compared successfully.
- Read-only `.venv/bin/python -c` probes using `unittest.mock` — validated **18 dataset × separator combinations**; tested schema mutations, unknown Git states, comparison mismatches and overwritten-result statistics.
- Offline Python probe with `HF_HUB_OFFLINE=1` — verified **3 MDX artefacts**, **7 Demucs files**, and all **66 rerun input digests** against freshly loaded audio.
- Python byte comparisons against `3c020c6` — **17/18 original holdout files unchanged**; procedural mixture baseline replaced.
- `git diff --check 681ae1d..HEAD` — two trailing blank-line warnings.
- A here-document probe failed because zsh required a temporary file; reran successfully with `python -c`.

Git emitted sandbox-related `xcrun` cache warnings but returned usable results.

## Round-2 finding status

| ID | Status | Evidence |
|---|---|---|
| M0-03a | **Resolved** | `run.py:73–105` enforces complete parameter/dataset key schemas and checks the metrics path against the imported module. Wrong `metrics_module`, unknown procedural field and omitted HPSS `kernel` all raise `ValueError`. All **18 committed combinations** validate. |
| M0-03b | **Partially resolved** | `run.py:150` rejects `git_dirty() → None` with exit **2**; `--allow-dirty` permits it, and line 196 records the override. However, `git_dirty() → False` combined with `git_rev() → "unknown"` still reaches dataset loading without an override. Revision inspection occurs only when constructing the final record at line 195. |
| M0-07 | **Resolved** | In-memory probes for numeric→`None`, changed role set, missing item and missing base file each return **1** with a diagnostic; identical inputs return **0**. A validity mismatch no longer produces misleading matching medians. The committed Kim vocal comparison retains **11.919 / 11.919 dB**. |

For the remaining **Medium** M0-03b gap, obtain and validate both Git revision and status before loading data; reject an unknown revision unless explicitly overridden, then record that same validated revision.

## New findings

### [M0-08] [Medium] Fix commit overwrites original holdout evidence with a partial probe

**Location:** `bench/results/procedural__holdout__baseline.mixture.json:22–25`; `bench/results/SUMMARY.md:128–132`.

**Evidence:** `bb18940` changes the original result from **4 items to 1**, removes `procedural-1001` through `procedural-1003`, and records `git_dirty: null`. Comparison against its parent confirms replacement of the original evidence. The summary still reports four items and the original aggregates:

- Vocal median: original **−3.495205 dB**, current JSON **−3.415136 dB**.
- Drum median: original **−4.938652 dB**, current JSON **−5.095137 dB**.

The seven-file rerun comparison does not include this configuration, so its successful exit does not detect the replacement.

**Impact:** The procedural baseline now uses a different item set from the other engines, and its committed summary is inconsistent with its JSON. This violates evidence-preservation expectations, but does **not** change the real-audio engine ranking or provisional decision; severity is Medium under the handoff scale.

**Fix:** Restore this file byte-for-byte from `bb18940^`. Keep partial probes outside the original results directory.

No evidenced **Critical or High** issue was found in the whole-branch sweep. Cached model artefacts verified, all rerun inputs reproduced, and the decision-driving real-audio results remain intact. The comparison reproduced the **0.247 dB** maximum atomic-stem median change and the disclosed **0.599 dB** accompaniment exception.

## Not verified

- Thirteen filesystem-dependent tests: four listening-packet tests, five artefact/download tests and four comparison tests. In-memory probes covered comparison control flow, but not filesystem behaviour.
- Full reruns of every ML configuration or the three-minute performance benchmark.
- Full MDX parity against an independent reference implementation.
- Linux CI, fresh installation, upstream licensing verification or hostile-decoder resistance.
- Unrecorded experiments and historical “scored once” discipline.

## Verdict

**Blocking findings: none.**

**Fit to merge as provisional research: yes.** Retain the remaining Medium M0-03b gap and new Medium M0-08 regression for correction; restore the overwritten evidence before treating the committed results as a complete preserved benchmark.