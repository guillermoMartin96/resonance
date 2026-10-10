<!-- Verbatim final message of: codex exec -s read-only (codex-cli 0.162.0, model gpt-6.1-sol, session 01a12428-a2c4-7f43-80c3-5c33616e2f5d), round-2 re-review of 3c020c6b73ad90f4c1e8e8c49123e35106396046, 2026-10-09. Not edited. -->

## Commands run

Reviewed HEAD `3c020c6b73ad90f4c1e8e8c49123e35106396046`. No files were modified or downloads performed.

- `cat docs/reviews/M0-review-handoff.md` and both round-1 review records — read instructions, findings and claimed dispositions.
- `git status --short`; `git rev-parse HEAD` — clean worktree; requested HEAD confirmed.
- `git diff --stat fe8a8f7..HEAD`; `git diff fe8a8f7..HEAD -- bench/stemforge_bench bench/scripts bench/tests bench/README.md` — inspected all implementation fixes and new tests.
- `rg --files -g AGENTS.md . ..` — no applicable `AGENTS.md` found.
- `cat` / `nl -ba` on adapters, datasets, metrics, downloads, listening-packet code, CI and decision records — inspected implementation and evidence.
- Read installed `demucs/pretrained.py` and `demucs/hf.py` — checked pinned-loader construction against upstream.
- `cd bench && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider -s` — **32 passed, 9 setup errors**, all caused by unavailable writable temporary directories.
- `PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 .venv/bin/python scripts/compare_results.py results/rerun-2026-10-09` — reproduced the review document’s comparison table.
- Read-only `.venv/bin/python -c` probes — verified cached artefact hashes, all 18 frozen-config combinations, all 66 rerun input digests, deterministic metric equality, tamper rejection, configuration omissions, unknown Git status handling and comparison of mismatched `None` values.
- In-memory download probe with mocked filesystem/network — corrupt-cache replacement, interrupted-download cleanup and checksum-failure cleanup passed.
- `git log --format='%h %s' -- 'bench/results/*holdout*'`; `git diff fe8a8f7..HEAD -- bench/results/*holdout*.json`; Python `git show` byte comparisons — all **18 original holdout JSONs remain byte-identical** to round 1.
- `git log --format='%h %s' 681ae1d..HEAD -- bench/config bench/data bench/stemforge_bench/datasets` — checked configuration/split history.
- `git diff --check fe8a8f7..HEAD`; final `git status --short` — no whitespace errors; clean worktree.

Git printed sandbox-related `xcrun` cache warnings, but these commands returned usable results.

## Findings

### [M0-03a] [Medium] Frozen configuration still accepts incomplete or contradictory settings

**Location:** `bench/stemforge_bench/run.py:73–95`.

**Evidence:** All 18 committed dataset/separator combinations pass validation. However, independent in-memory probes also accepted:

- `metrics_module: "wrong.py"`;
- an unknown procedural dataset setting;
- removal of HPSS’s frozen `kernel` parameter.

The validator checks supplied separator keys and selected dataset fields; it does not enforce a complete schema or validate `metrics_module`.

**Impact:** The fix rejects the original contradictory seeds/durations/parameters, but the claim that “every frozen setting” describes exactly what executes remains too strong. An omitted parameter can silently follow a changed adapter default. Current committed results are unaffected.

**Recommended fix:** Require the complete expected configuration schema, reject unknown execution fields, and validate the metrics-module identity.

### [M0-03b] [Medium] Holdout provenance gate permits an unverifiable source tree

**Location:** `bench/stemforge_bench/run.py:37–51,121`.

**Evidence:** Git failures return `None`; the holdout gate tests `if dirty`, so `None` passes. A probe substituting `git_dirty() → None` reached dataset loading without `--allow-dirty`.

**Impact:** Runs outside a usable Git checkout, or with failed Git inspection, can proceed without verified implementation identity. This does not affect the committed reruns, which record a known revision and `git_dirty: false`.

**Recommended fix:** Reject unknown Git status/revision for holdout unless explicitly overridden, and record the override.

### [M0-07] [Medium] Result comparison silently hides SDR validity changes

**Location:** `bench/scripts/compare_results.py:37–44`.

**Evidence:** I changed one rerun Kim vocal SDR to `None` in memory. The script discarded that item from **both** runs, printed matching vocal medians of **11.194 dB** instead of the complete-set **11.919 dB**, reported zero delta and returned **0**.

**Impact:** A regression that loses a valid score can appear reproducible. The committed reruns do not contain this mismatch, so their independently checked comparison remains valid.

**Recommended fix:** Check role sets and per-item `None` validity before filtering; report mismatches and return nonzero. Compute each run’s median from its own valid observations.

## Round-1 finding status

| ID | Status | Evidence |
|---|---|---|
| M0-01 | **Resolved** | Cached ONNX files and parameter table match pins. Loader verifies both before parsing/session creation; substituted hashes were rejected before session construction. |
| M0-02 | **Resolved** | Both pinned revisions resolve offline; all **7 YAML/weight files** match expected hashes. Substituted bytes are rejected. Bag construction matches installed upstream. |
| M0-03 | **Partially resolved** | Committed settings validate, mismatch tests pass, and all **66** rerun input digests reproduce. Schema completeness and unknown Git status remain gaps above. |
| M0-04 | **Resolved** | Real-weight repeatability test passed: identical outputs across differing caller RNG states, with Python RNG state preserved. Rerun effects are quantified below. |
| M0-05 | **Resolved** | Platform-unit tests pass; runner and performance probe now share `platform_info.peak_rss_mb`. |
| M0-06 | **Resolved** | Code verifies `.part` content before atomic replacement. In-memory probes confirmed repair and cleanup on interruption/checksum failure. |

## Verified OK

- **Demucs loader parity:** The adapter uses the same `load_safetensors_model` ordering and `BagOfModels(models, weights, segment)` construction as installed `get_hf_model`, followed by `eval()`. The verified fine-tuned YAML retains its four source-specific weighting rows.
- **Artefact enforcement:** MDX verifies both models and the parameter table before use. Demucs verifies every selected YAML/safetensors file before constructing models.
- **Deterministic reruns:** All metrics match exactly for **26 items** across HPSS and both MDX configurations—not merely rounded SDR values.
- **Rerun provenance:** All seven files contain frozen hash `cb98142e…`, revision `bf242952…`, and `git_dirty: false`. Freshly loaded audio reproduces all **66** input hashes.
- **Demucs comparison:** Largest absolute atomic-stem median change is approximately **0.247 dB**. Accompaniment changes reach **0.599 dB** on BabySlakh-ft and **0.272 dB** on vocalmix-ft. The detailed review document correctly discloses the accompaniment exception.
- **Bass conclusion:** BabySlakh bass changes from **5.261 / 5.282 dB** to **5.376 / 5.234 dB** for standard/fine-tuned Demucs. The ordering reverses; treating this comparison as inconclusive is justified. This is not a statistical equivalence test.
- **Original evidence preserved:** All **18** original holdout files are byte-identical to round 1. The new evidence is stored separately.
- **Decision scope:** DR-0001 remains provisional, separates code licences from weight rights and restricts ML use. DR-0002 still reports **zero** expanded-corpus items. Pending listening evidence remains disclosed.
- **Regression checks:** STFT parity, baseline contracts, MDX contract, Demucs contract, metrics tests and new executable provenance tests passed.

## Not verified

- Nine filesystem-dependent tests: four listening-packet tests and five provenance/download tests require writable temporary directories. Targeted read-only probes covered artefact rejection and download control flow, but not actual filesystem atomicity.
- Full ML reruns of every configuration; I independently checked committed rerun data and executed the real-weight contract/repeatability tests.
- Full MDX parity against the absent reference environment.
- Linux CI execution, fresh dependency installation, upstream revision history and independent legal verification.
- Hostile-decoder resistance or download resource limits.
- Unrecorded experiments or whether holdout was historically scored exactly once.

## Verdict

**Remaining blocking findings: none.**

The two round-1 High findings are resolved. I found no new evidenced Critical/High issue in the reviewed branch. M0 is fit to merge as **provisional research**, with the three Medium findings above retained for correction and the stated verification limits preserved.