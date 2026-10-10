# DR-0003 — Development runtime and worker platform

Status: **APPROVED — 2026-10-09, by the owner/technical lead.** Native Intel macOS CPU development, pinned, Node 22 LTS. Compatibility check passed (below).

## Context (evidence: `docs/research/M0-environment.md`)
The development machine is an **Intel x86_64 Mac** (i9-9880H, 32 GB, no CUDA). Upstream ML runtimes no longer publish Intel-macOS wheels:
- torch: last is **2.2.2** (Mar 2024) → Python ≤ 3.12, `numpy<2`.
- onnxruntime: last is **1.23.2** (Oct 2025).
- demucs 4.1.0 needs `sphn` (Rust), which has no Intel-Mac wheel → installed with `--no-deps`.
- python-audio-separator ≥ 0.22 is not installable at all on this machine.
Node default is 18.7.0 (EOL); current Vite needs ≥ 20.19 / 22.12.

## Options
A. **Native Intel macOS, CPU-only, pinned** (what M0 used): Python 3.12.15 (uv-managed), torch 2.2.2, onnxruntime 1.23.2, numpy 1.26. Simplest today; no security or bug-fix updates for torch; each new engine may hit the same wall.
B. **Native API + UI, separation worker in a Linux x86_64 Docker container** (Docker 20.10.16 is installed and running). Current wheels, same JSON worker contract as ARCHITECTURE.md. Costs: container build, Docker VM memory limit is 8 GB today (raise to ≥ 12 GB), bind-mount I/O overhead, old Docker version (20.10) may need an update.
C. **A + B staged**: M1 ships A (works now, benchmarked), with the worker boundary kept JSON-only so B is a drop-in later.
D. Different hardware (Apple Silicon / Linux+CUDA) for a GPU worker — requires budget approval; not proposed now.

Node: pin **Node 22 LTS** via `.nvmrc` (`nvm install 22`, user-level, reversible). Node 25.4.0 is already present but is not LTS.

## Recommendation
**C**, plus Node 22 LTS. It unblocks M1 on proven versions without closing off newer engines.

## Consequences
A/C pin us to torch 2.2.2 on this machine; reversible by moving the worker (B). B adds a container build to the dev setup. Installing Node 22 changes nothing system-wide (nvm is per-user).

## Decision record (2026-10-09)
**Approved:** native Intel macOS CPU development with pinned dependencies (option A, kept container-ready as in C) and **Node 22 LTS**, provided compatibility checks pass.

Conditions:
1. The worker stays portable to Linux (CI runs the bench suite on `ubuntu-latest`, see `.github/workflows/ci.yml`).
2. No new infrastructure or containerisation in M0.
3. Installation limitations and a reproducible setup are documented (`bench/README.md`, `docs/research/M0-environment.md`).
4. Platform-specific logic stays isolated (today: the `--no-deps demucs` install step and the RSS unit conversion in `run.py`/`perf_probe.py`).

### Compatibility check (2026-10-09, this machine)
| Check | Result |
|---|---|
| `nvm install 22` (per-user) | Node **v22.23.3** (LTS "Jod"), npm 10.9.9, `x64 darwin` |
| Vite 7.3.7 install + `vite build` of a trivial page, in a scratch directory outside the repo | ok |
| Python bench suite on pinned versions (`pytest -q`) | 18 passed |
| Same suite on Linux x86_64 (GitHub Actions) | see CI on the PR |

`.nvmrc` pins `22`. Node 25.4.0 and 18.7.0 remain installed but are not used by the project.
