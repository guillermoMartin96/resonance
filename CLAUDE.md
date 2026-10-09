# Claude Code operating instructions

You are implementing StemForge, a browser-based, AI-assisted sample extraction workstation. The core user value is isolating **actual recorded sounds** and reusing them, with provenance and rights metadata.

Read in order: `docs/PRODUCT.md`, `docs/architecture/ARCHITECTURE.md`, `docs/research/RESEARCH_GATES.md`, `docs/milestones/M1.md`, `docs/ENGINEERING_PLAYBOOK.md`.

Rules:
- Work in a dedicated feature branch. Commit coherent checkpoints; push only if a remote and permissions exist. Never merge without approval.
- Do not silently make consequential product, license, model, infrastructure, or budget choices. Record decision requests under `docs/decisions/requests/`.
- No Spotify audio ripping, DRM circumvention, streaming capture, or unauthorized download paths. Spotify metadata/link support may be researched separately.
- Do not assume separated audio is artifact-free, an isolated original studio track, or legally reusable.
- Use provider-neutral adapters and reproducible benchmark evidence; no model selection by popularity alone.
- Prefer CPU-capable local development with an optional GPU worker; detect and document platform constraints before installing heavy dependencies.
- Write tests and validation evidence for each user-visible capability. No external paid services without approval.
- Keep the core usable without an LLM; AI guidance is an optional orchestration layer, never required for extraction.
- If a gate fails, report it and stop that path instead of fabricating results.
