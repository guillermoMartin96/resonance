<!-- Verbatim final message of: codex exec -s read-only (codex-cli 0.162.0, model gpt-6.1-sol, session 01a12430-3316-7691-aa54-e51d91c16c4e), round-4 review of 524cdda, 2026-10-09. Not edited. -->

## Commands run

Reviewed HEAD `524cddaf4bb720105e2f2d8ff69d79694c8a5b54`. No files modified or downloads performed.

- `cat docs/reviews/M0-review-handoff.md docs/reviews/evidence/M0-codex-review-round3.md` — read constraints and prior findings.
- `git rev-parse HEAD`; `git status --short`; `git show HEAD` — confirmed requested commit, clean worktree, and inspected fixes.
- Python byte comparison using `git ls-tree` and `git show 0ec5611:<path>` — **all 38 original result files byte-identical**, including `SUMMARY.md`; all **18 holdout pins match original bytes**.
- `cd bench && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider -s` — **38 passed, 15 setup errors**, all caused by unavailable writable temporary directories.
- Read-only Python probes using `unittest.mock` — unknown status, unknown revision, and both unknown each exit **2 before dataset loading**; `--allow-dirty` permits each and records the override. Known revision sampled once and recorded unchanged.
- Direct invocation of the preservation guard, with mocked byte mutations — original passes; independent modification of **each of the 18 pinned files** triggers an assertion.
- In-memory execution of `scripts/summarize.py`, intercepting its write — generated summary matches committed `SUMMARY.md` exactly.
- `cd bench && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/compare_results.py results/rerun-2026-10-09` — **exit 0**, seven reruns compare successfully.
- `git diff 681ae1d..HEAD --stat`; targeted diffs, reads and history — inspected datasets, metrics, adapters, downloads, provenance, listening packets, CI and decision evidence.
- `git diff --check 681ae1d..HEAD` — two existing trailing blank-line warnings.

## Finding status

| ID | Status | Evidence |
|---|---|---|
| M0-03b | **Resolved** | `run.py:141–155` obtains revision and status before dataset loading and rejects either unknown state unless overridden. `run.py:195` records that same revision. Independent probes confirmed rejection, override behavior and single revision sampling. |
| M0-08 | **Resolved** | All 38 files present at `0ec5611` are restored/preserved exactly. `HOLDOUT_SHA256.json` pins the original 18 holdout JSONs; mutation probes confirm detection. The offending test now supplies `--out tmp_path`, replaces the dataset loader with an empty stub, and asserts loading never occurred. It cannot overwrite committed results through this execution path, even if the gate regresses. |

The preservation guard covers the **18 holdout JSONs**; it does **not** pin `SUMMARY.md`, dev results or performance results. Their current preservation was independently verified against `0ec5611`.

## New findings

none.

No evidenced regression from `524cdda`, or Critical/High finding in the inspected `681ae1d..HEAD` diff.

## Not verified

- Fifteen filesystem-dependent tests could not complete setup, including both parameterized Git-state tests. In-memory probes independently verified the Git gate behavior.
- Full benchmark reruns, the three-minute performance probe, and independent full MDX reference parity.
- Linux CI, fresh installation, upstream licensing facts, hostile-decoder resistance, or unrecorded historical experiments.

## Verdict

**Blocking findings: none.**

**Fit to merge as provisional research: yes.**