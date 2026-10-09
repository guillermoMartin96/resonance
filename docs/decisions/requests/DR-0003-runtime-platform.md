# DR-0003 — Development runtime and worker platform

Status: OPEN — owner approval needed before M1 scaffolding pins versions.

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

## Approval
Owner selects. No runtime upgrades or installs outside project venvs have been made.
