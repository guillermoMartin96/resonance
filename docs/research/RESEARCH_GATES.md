# Research and validation gates

## R1 — Environment and feasibility (before installation)
Inventory OS/architecture, Python/Node versions, available memory/storage, CPU/GPU, package availability, and license constraints. Offer supported local alternatives. Do not force an incompatible Python upgrade.

## R2 — Separator evaluation (before commitment)
Compare at least two viable candidate approaches (e.g. Demucs-family and MDX/UVR-compatible or other actively maintained option) using primary sources for model licenses, weights, dependencies and deployment support. Do not assume named projects remain maintained. Include a no-separation baseline for playback pipeline tests. Document tradeoffs: drums/bass/vocals/other fidelity, bleed, artifacts, CPU runtime, memory, installation complexity, commercial licensing.

## R3 — Evaluation dataset
Create reproducible, legally usable synthetic mixtures from isolated licensed/permissive stems; retain source attribution and license. Separate development/tuning examples from untouched holdout examples. Do not include copyrighted commercial songs in repo. For subjective listening, use a documented blind A/B rubric; where ground truth exists, report SI-SDR/SDR with caveats, stem-specific metrics, and runtime factor.

## R4 — Acceptance gates
- Upload/playback end-to-end on target machine with supported formats and useful errors.
- At least one separator runs end-to-end on a short authorized sample.
- Outputs have expected number of stems, playable durations/channels, provenance, and non-silent content where applicable.
- Benchmark results and listening observations recorded, including artifacts and failure cases.
- No model chosen until comparison evidence and licensing review are documented.

## R5 — Rights and integration
Research provider-specific API and content-use terms before adding Spotify, Freesound, Splice, Looperman, or others. Public access alone is insufficient. Never implement DRM bypass, scraping prohibited audio, or protected-stream capture.

## Decision output
Write `docs/decisions/requests/DR-0001-separator-choice.md` with candidates, evidence, recommendation, limitations and explicit approval needed.

## M0 status (2026-10-09; DR-0001/2/3 approved the same day)
| Gate | Status | Evidence |
|---|---|---|
| R1 | done | `M0-environment.md` (Intel macOS wheel ceilings; DR-0003) |
| R2 | done | `M0-separator-evaluation.md` §1 (Demucs, MDX-Net, Open-Unmix screened, HPSS + mixture baselines) |
| R3 | done, with gaps | `BENCHMARK_PROTOCOL.md`; corpus expansion approved in DR-0002 but **0 items acquired**; blind listening packet ready (`LISTENING_TEST.md`), **owner results pending** |
| R4 | met for research harness | `docs/proof/M0-proof.md`; upload/playback is M1 scope |
| R5 | not started | Spotify/sample-library terms research deferred; no integration code exists |
