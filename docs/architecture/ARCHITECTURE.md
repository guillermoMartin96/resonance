# Proposed architecture (provisional)

## Components
- Browser UI: TypeScript + React + Vite (proposed), waveform display, file input, job status, solo/mute playback, clip selection.
- Local API: Python + FastAPI (proposed), upload validation, job creation/status, media manifests, rights metadata.
- Worker: asynchronous separation job with provider-neutral `Separator` interface; CPU baseline, optional GPU; timeout/cancellation/resource limits.
- Storage: filesystem artifacts and SQLite metadata for M1; stable IDs and explicit migrations; cloud migration deferred.
- Audio: server-side normalization and deterministic WAV output via available FFmpeg or equivalent, with pinned versions and licensing review.

## Interfaces
`POST /api/assets` upload + rights declaration; `GET /api/assets/{id}`; `POST /api/assets/{id}/separations`; `GET /api/jobs/{id}`; `GET /api/separations/{id}`; `GET /api/media/{id}`. These are proposed contracts, not yet finalized.

## Core entities
`SourceAsset(id, filename, sha256, duration, sample_rate, source_url?, rights_basis, created_at)`
`SeparationJob(id, asset_id, model_id, model_version, params, status, error, timing)`
`Stem(id, job_id, role, media_path, sample_rate, channels, duration)`
`Clip(id, stem_id, start_ms, end_ms, label, provenance)`

## Design constraints
Audio files stay outside the web static directory; use validated IDs and scoped streaming endpoints. Bound upload size, length, concurrency and disk usage. Reject unsupported formats and unsafe filenames. Use deterministic job state and cleanup. Store model version, parameters and input hash for reproducibility. No API keys in client or repository. Never promise a perfectly isolated original source; separation estimates components from a mix.

## Future boundaries
Provider-neutral separation adapters; analysis adapters for beat/key; sample-library connector adapters with license filtering; optional LLM planner produces reviewable edit operations, not direct arbitrary code execution.
