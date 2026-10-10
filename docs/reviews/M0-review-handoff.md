# M0 independent review — handoff brief

You are an independent reviewer for StemForge Milestone 0 (research). You did not write this code. Your job is to find real defects. Don't summarise the authors' claims. **Inspect the actual implementation and evidence files, run what you can, and verify claims against code and data.** Assume the summary documents may be wrong.

## Target
- Repository: this working directory, branch `feature/m0-research`. PR: https://github.com/guillermoMartin96/resonance/pull/1 (draft).
- Diff under review: `git diff 681ae1d..HEAD` (`681ae1d` = main). Everything under `bench/`, `docs/`, `.github/`.
- Environment: Intel macOS x86_64, CPU only. A ready venv exists at `bench/.venv` (Python 3.12, torch 2.2.2, onnxruntime 1.23.2, demucs 4.1.0). Data and weights are already downloaded in `bench/.cache/` (gitignored). The sandbox is read-only and has no network, so run tests as
  `cd bench && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`
  and write any scratch scripts to stdin (`.venv/bin/python - <<'EOF' … EOF`), not to disk.
- Do not modify files. Do not download anything.

## Review priorities (in order)
1. **Benchmark methodology, holdout integrity, data leakage.** `bench/stemforge_bench/datasets/*`, `bench/config/frozen.json`, `bench/data/manifest.json`, `bench/stemforge_bench/run.py`, git history (`git log -p 681ae1d..HEAD -- bench/config bench/data bench/stemforge_bench/datasets`). Were the dev/holdout splits fixed before holdout scoring? Can a holdout item, vocal or accompaniment, appear in dev? Does the frozen-config check actually bind what ran (params, code, data)? Was anything tuned after seeing holdout numbers?
2. **SDR calculation correctness and aggregation.** `bench/stemforge_bench/metrics.py`, `bench/scripts/summarize.py`, `bench/results/*.json`, `bench/results/SUMMARY.md`. Check the global-SDR / SI-SDR / projection SIR/SAR / silent-leak definitions, edge cases (silent references, None handling), median/mean aggregation, and whether the numbers quoted in `docs/research/M0-separator-evaluation.md`, `docs/proof/M0-proof.md` and `docs/decisions/requests/DR-0001-separator-choice.md` match the result JSONs. Recompute a sample.
3. **MDX ONNX runner parity and signal-processing correctness.** `bench/stemforge_bench/separators/mdx_onnx.py` against the reference algorithm (python-audio-separator `mdx_separator.py`, UVR MDX). Check STFT/ISTFT, channel/real-imag packing, bin zeroing, chunking, overlap windows and division, trim/padding, normalisation (peak scaling), the compensate factor, resampling, and secondary-stem derivation. Also `demucs_adapter.py` (normalisation, resampling, shift seeding) and `baselines.py`.
4. **Reproducibility, dependency compatibility, checksum verification.** `bench/requirements.lock.txt`, `bench/README.md`, `bench/scripts/fetch_data.py`, `bench/scripts/fetch_models.py`, `.github/workflows/ci.yml`, `docs/research/M0-environment.md`. Are all downloaded artefacts (dataset, vocals, ONNX weights, the UVR parameter table, Demucs weights) checksum-verified *before use*? Can the results be reproduced from the documented commands?
5. **Security of audio decoding and external downloads.** URL handling, redirects, partial-download handling, tar extraction, file sizes, libsndfile decoding of untrusted files, subprocess use.
6. **Licensing claims and commercial-use restrictions.** `bench/data/manifest.json`, `SeparatorInfo.weights_license`, the DR records, the proof. Are licences correctly stated? Is there anywhere the docs imply code licence ⇒ weight rights, or imply commercial use is OK? Are attribution requirements (CC BY / CC BY-SA) met?
7. **Missing tests, doc inconsistencies, portability risks.** `bench/tests/*`, Linux portability (CI), platform-specific code.

Also check `bench/scripts/make_listening_packet.py` (blinding correctness) and the approved decision records `docs/decisions/requests/DR-000{1,2,3}-*.md` against the evidence.

## Severity scale
- **Critical**: results or conclusions are invalid, there is a security hole, or a licence violation.
- **High**: a material error that could change an engine ranking or a decision, or an unverified artefact used in results.
- **Medium**: a correctness or reproducibility gap that doesn't change current conclusions.
- **Low**: a nit, documentation gap, or hardening.

## Required output (markdown)
1. `## Commands run`: each command and a one-line result.
2. `## Findings`: one entry per finding, highest severity first:
   `### [ID] [Severity] title`, then **Location** (file:line), **Evidence** (what you ran or read, with numbers), **Impact**, **Recommended fix**.
3. `## Verified OK`: the things you checked and found correct, with evidence. Be specific.
4. `## Verdict`: blocking findings (Critical/High) or "none", and whether M0 is fit to merge after they are fixed.

Only report findings you have evidence for. If you can't verify something, say so under a `## Not verified` heading instead of guessing.

---

# Round 2 — re-review of fixes

Round 1 findings (your earlier output) are in `docs/reviews/evidence/M0-codex-review-round1.md`; the authors' claimed dispositions are in `docs/reviews/M0-review.md`. **Don't take the dispositions on trust.** For the fix diff `git diff fe8a8f7..HEAD`:
1. For each of M0-01…M0-06, verify against the code (and by running tests or probes) whether the finding is actually resolved. Answer **Resolved / Partially resolved / Not resolved**, with evidence.
2. Look for regressions or new defects introduced by the fixes: `separators/demucs_adapter.py` (pinned loading must build the same model as `demucs.pretrained.get_model`), `separators/mdx_onnx.py`, `run.py` (`check_frozen`, `item_digest`, dirty-tree gate), `scripts/fetch_models.py`, `scripts/compare_results.py`, `stemforge_bench/platform_info.py`, `tests/test_provenance.py`.
3. Check the re-run evidence in `bench/results/rerun-2026-10-09/` against the originals in `bench/results/`. Are the claims in `docs/reviews/M0-review.md` ("deterministic engines identical", "Demucs median Δ ≤ 0.25 dB", "bass is a tie") supported? Were the original holdout JSONs left unmodified (`git log -- bench/results/*holdout*`)?
4. Confirm that no new Critical/High issue exists anywhere in the branch.

Use the same output format as round 1, plus a `## Round-1 finding status` table. End with `## Verdict`: remaining blocking findings, or "none".
