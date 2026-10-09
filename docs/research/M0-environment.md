# M0 / R1 — Environment and feasibility

Audited 2026-10-09 on the owner's development machine. Commands are recorded in `docs/proof/M0-proof.md`.

## Machine

| Item | Value |
|---|---|
| OS | macOS 26.2 (build 25C56), Darwin 25.2.0 |
| CPU | Intel Core i9-9880H @ 2.3 GHz, **x86_64**, 8 cores / 16 threads |
| RAM | 32 GB |
| Disk | 932 GB volume, ~711 GB free at audit time |
| GPU | Intel UHD 630 + AMD Radeon Pro 5500M (Metal 3). **No CUDA.** |
| Git | 2.50.1 (Apple); remote `origin` = github.com/guillermoMartin96/resonance; `gh` 2.102.0 |
| Python | system `/usr/bin/python3` 3.9.6 (too old: demucs/FastAPI need ≥3.10); uv-managed CPython **3.12.15** at `~/.local/bin/python3.12` (the `uv` binary itself is not on PATH) |
| Node | nvm: v18.7.0 (default, end-of-life), v25.4.0, v11.7.0. Current Vite (8.3.x) requires `^20.19 \|\| >=22.12` |
| Media tools | **no `ffmpeg`, `ffprobe` or `sox`** on PATH |
| Containers | Docker 20.10.16; daemon running, Linux VM x86_64, 8 CPUs, 8 GB |
| Package mgr | Homebrew 7.0.8 |

## Platform constraint that dominates everything: Intel macOS

Upstream ML runtimes have stopped publishing Intel-macOS wheels:

| Package | Last Intel-macOS wheel | Latest release (2026-10-09) | Effect |
|---|---|---|---|
| torch | **2.2.2** (Mar 2024), cp38–cp312 | 2.14.1 | Python ≤ 3.12 and `numpy<2` on this machine |
| torchaudio | 2.2.2 | 2.11.0 | not needed (we avoid it) |
| onnxruntime | **1.23.2** (Oct 2025), cp310–cp313 | 1.31.0 | still recent enough; ceiling will age |
| numba / llvmlite | 0.62.1 / 0.45.1 | newer | only matters for librosa-based tools |
| sphn (Kyutai audio I/O) | 0.1.4 | 0.2.1 | **demucs 4.1.0 requires sphn ≥ 0.1.12 → no wheel → source build needs Rust** |

Consequences:
- **Demucs 4.1.0** declares Intel-Mac pins itself (`torch<2.3`, `numpy<2` on darwin/x86_64), but `pip install demucs` **fails** here because `sphn` must be compiled from Rust. Workaround used for M0: `pip install --no-deps demucs==4.1.0` plus its other dependencies explicitly; `sphn` is only imported by `demucs/api.py` (file decoding), which our adapter does not use. `pip check` reports the missing `sphn` — expected and documented.
- **python-audio-separator** (the maintained UVR/MDX wrapper): current 0.47.0 requires `torch>=2.3` and `numpy>=2` on Intel Macs → **not installable**. The last compatible line (≤0.21.x, mid-2024) installs only after pinning `numba==0.62.1`/`llvmlite==0.45.1`, needs a system `ffmpeg` binary, and has a stem-normalisation bug (see evaluation doc). It was used only in a throwaway venv as a parity reference.
- During the first failed demucs install, pip's build backend tried to bootstrap a Rust toolchain into `~/Library/Caches/puccinialin`. That cache pre-dates this session (Sep 25) and was left untouched.
- GPU acceleration is effectively unavailable: no CUDA; torch 2.2's MPS backend on AMD/Intel Macs is not something to depend on; ONNX Runtime offers `CoreMLExecutionProvider`, untested here. **Plan for CPU-only on this machine.**

## Supported local setup (what M0 actually used)

```
~/.local/bin/python3.12 -m venv bench/.venv
bench/.venv/bin/python -m pip install "torch==2.2.2" "onnxruntime==1.23.2" "numpy<2" \
    "soundfile==0.13.1" scipy pytest pyyaml einops huggingface-hub "julius>=0.2.3" \
    "lameenc>=1.2" safetensors tqdm
bench/.venv/bin/python -m pip install --no-deps "demucs==4.1.0"
```
Exact resolved versions: `bench/requirements.lock.txt` (40 packages). Install time ≈ 40 s on a warm pip cache; venv ≈ 1.0 GB.
Audio decoding uses libsndfile (bundled with `soundfile` 0.13.1), which reads WAV/FLAC/OGG/MP3 — **no ffmpeg needed** for these formats.

## Alternatives offered (not adopted without approval — see DR-0003)

1. **Stay native on Intel macOS, CPU-only** (used for M0). Pinned to torch 2.2.2 / onnxruntime 1.23.2; no further upgrades possible for torch.
2. **Linux x86_64 container for the worker** (Docker is installed and running). Gets current torch/onnxruntime/audio-separator wheels; costs container setup, an 8 GB VM memory cap (raise in Docker settings), and slower file I/O through bind mounts.
3. **Apple-Silicon or Linux/CUDA machine** for a GPU worker later — out of scope until budget approval.

## Node / frontend readiness
Node 18.7.0 (default) is end-of-life and too old for current Vite. Node v25.4.0 is already present in nvm (non-LTS). M1 should pin an LTS (22.x) via `.nvmrc`; installing it with `nvm install 22` is user-level and reversible but is still listed for approval in DR-0003.
