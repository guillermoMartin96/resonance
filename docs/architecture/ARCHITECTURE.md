# Proposed architecture (provisional)

Status: proposal updated with M0 evidence (2026-10-09). Nothing here is final until M1 is approved; the separation engine is **not** selected (DR-0001).

## Minimum architecture for M1

```
Browser (React + TS + Vite)                     local machine only, single user
  │  upload + rights form, waveform, job status, solo/mute/A-B playback
  ▼  HTTP/JSON + range-request audio streaming
Local API (Python 3.12 + FastAPI)
  │  validation, IDs, SQLite metadata, provenance manifests, scoped media serving
  │  enqueue job row ──────────────┐
  ▼                                ▼
Filesystem storage            Separation worker (separate OS process)
  data/assets/<id>/source.*      polls SQLite for queued jobs; runs ONE job at a time
  data/jobs/<id>/stems/*.wav     in a child process with timeout + memory guard;
  data/jobs/<id>/manifest.json   calls a Separator adapter chosen by separator_id
                                     │
                                     ▼
                     Separator adapters (provider-neutral; see below)
                     baseline.mixture | baseline.hpss | demucs.* | mdx.* | (future: remote/GPU)
```

Why a separate worker process (M0 evidence):
- Model runs take ~0.7–1.2× real time on this CPU and use several GB of RAM (`docs/research/M0-separator-evaluation.md`); the API must stay responsive.
- Killing a process is the only reliable cancellation/timeout for torch/onnxruntime inference.
- The Intel-Mac wheel ceilings (torch 2.2.2, onnxruntime 1.23.2) make it likely the worker will later move to a Linux container or another host; the API should not import ML runtimes at all.
- Crash isolation: a model segfault or OOM marks the job failed instead of taking down the API.

## Provider-neutral separation interface

Validated in M0 by four very different implementations (identity, classical DSP, Demucs/torch, MDX/onnxruntime) behind one protocol. Source: `bench/stemforge_bench/separators/base.py`; to be promoted to a product package once DR-0001 is approved.

```python
CANONICAL_ROLES = ("vocals", "drums", "bass", "other", "accompaniment")

@dataclass(frozen=True)
class SeparatorInfo:
    id: str                 # "demucs.htdemucs", "mdx.Kim_Vocal_2", "baseline.mixture"
    engine: str             # implementation family
    engine_version: str
    model_name: str
    native_sample_rate: int
    roles: tuple[str, ...]  # canonical roles this adapter emits
    code_license: str
    weights_license: str    # "unstated" is an explicit, surfaced value
    weights_sha256: tuple[str, ...]
    params: dict

class Separator(Protocol):
    info: SeparatorInfo
    def load(self) -> None: ...
    def separate(self, audio: np.ndarray, sample_rate: int) -> dict[str, np.ndarray]: ...
        # audio (channels∈{1,2}, samples) float32; returns every role in info.roles,
        # same shape and rate as input; must not mutate input; raises SeparationError
```

Rules the adapters already follow:
- Adapters own resampling/channel conversion to and from their native format; callers never need to know the model's rate.
- Stems that are derived rather than predicted (e.g. Demucs `accompaniment = drums+bass+other`, MDX `secondary = mix − primary × compensate`) are produced by the adapter and flagged in provenance.
- `validate_input` / `validate_output` enforce shape, finiteness and role completeness for every engine.
- Optional engines import their runtime lazily, so the core app runs with only `baseline.*` installed (no torch/onnxruntime required) — this is the M1 fallback if DR-0001 is unresolved.

### Worker boundary (JSON, so the worker can be remote later)
```jsonc
// SeparationRequest
{"job_id": "...", "input_path": "data/assets/<id>/source.wav", "input_sha256": "...",
 "separator_id": "demucs.htdemucs", "params": {}, "limits": {"timeout_s": 900, "max_rss_mb": 8000}}
// SeparationResult
{"job_id": "...", "status": "succeeded|failed", "error": {"code": "...", "message": "...", "hint": "..."},
 "separator": { /* SeparatorInfo */ }, "timing": {"load_s": 3.1, "separate_s": 140.2, "rtf": 0.78},
 "stems": [{"role": "vocals", "path": "data/jobs/<id>/stems/vocals.wav", "sha256": "...",
            "sample_rate": 44100, "channels": 2, "duration_s": 180.0, "derived": false}]}
```

## API (proposed contracts)

| Method & path | Purpose |
|---|---|
| `GET /api/separators` | list installed adapters with roles, licence notes and availability (so the UI can show "weights licence: unstated") |
| `POST /api/assets` | multipart upload + rights declaration `{rights_basis, source_url?, license?, acknowledgement: true}`; returns `SourceAsset` |
| `GET /api/assets/{id}` | metadata incl. sha256, duration, sample rate, channels |
| `POST /api/assets/{id}/separations` | `{separator_id, params?}` → `SeparationJob` (status `queued`) |
| `GET /api/jobs/{id}` | `queued → running → succeeded | failed | cancelled`, progress, timings, error `{code, message, hint}` |
| `POST /api/jobs/{id}/cancel` | kills the worker child if running |
| `GET /api/separations/{id}` | stems + provenance manifest |
| `GET /api/media/{id}` | scoped, range-capable audio streaming by opaque ID (never by path) |

## Core entities
`SourceAsset(id, filename, sha256, duration, sample_rate, channels, source_url?, rights_basis, license?, created_at)`
`SeparationJob(id, asset_id, separator_id, engine_version, weights_sha256, params, status, error, timing, created_at, updated_at)`
`Stem(id, job_id, role, derived, media_path, sha256, sample_rate, channels, duration)`
`Clip(id, stem_id, start_ms, end_ms, label, provenance)` (M2)

Each job writes `manifest.json` next to its stems: source asset hash + rights declaration, full `SeparatorInfo` (including weights licence and hashes), params, timings, and the fixed notice *"Stems are model estimates of components of the mix, not original multitrack recordings, and may contain bleed and artifacts. Separation does not grant any rights to the source recording."*

## Design constraints
Audio files stay outside the web static directory; use validated IDs and scoped streaming endpoints. Bound upload size, duration, concurrency (one separation at a time on CPU) and disk usage. Reject unsupported formats and unsafe filenames. Decode with libsndfile (WAV/FLAC/OGG/MP3) — no ffmpeg dependency needed for M1 formats. Deterministic job state: on startup, any `running` job without a live worker is marked `failed` (no orphaned running state). Store engine version, weights hash, params and input hash for reproducibility. No API keys in client or repository. Never promise a perfectly isolated original source.

## Proposed repo layout (M1)
```
apps/web/                 React + TS + Vite UI
services/api/             FastAPI app (no ML imports)
services/worker/          job runner; depends on packages/separation
packages/separation/      Separator protocol, registry, adapters (promoted from bench/)
bench/                    M0 research harness, benchmark data manifest, results
docs/
```

## Future boundaries
Remote/GPU worker speaking the same JSON contract; analysis adapters for beat/key; sample-library connector adapters with licence filtering; optional LLM planner produces reviewable edit operations, never arbitrary code execution, and is never required for extraction.
