# DR-0002 — Benchmark corpus expansion (real multitrack material)

Status: **APPROVED — 2026-10-09, by the owner/technical lead.** Expansion approved; the expanded evaluation is **not started** (no audio acquired yet). See *Decision record*.

## Context
The M0 benchmark (`docs/research/BENCHMARK_PROTOCOL.md`) uses:
- CC0 procedural fixtures (generated) — valid for drums/bass sanity and CI, **invalid for vocals** (no model recognises formant-synth vowels as singing);
- BabySlakh (CC BY 4.0) — sample-based MIDI renders, 16 kHz, no vocals;
- five unaccompanied vocal recordings from Wikimedia Commons (CC0, US-government public domain, CC BY-SA 4.0) mixed over BabySlakh.

This is enough to rank engines coarsely but not to judge the product's core claim on *real* full-band productions: 16 kHz material hides high-frequency artifacts, and there is no live-band bleed, mastering or genre coverage (hip-hop/electronic, the target users).

## Options
A. **Keep the current corpus** for M1; revisit before M4. Zero cost, zero new terms. Weak on full-band and genre realism.
B. **QUASI database** (Telecom Paris): 11 real multitrack songs with several professional mixes each. Per-song CC licences (BY, BY-SA, BY-NC, BY-NC-SA). Requires accepting terms via a subscription form. Use only the non-NC songs for benchmarking; nothing redistributed.
C. **ccMixter a cappellas and stems** (mostly CC BY 3.0, made for remixing, often hip-hop/electronic, full-band 44.1 kHz). Direct downloads returned HTTP 403 to unauthenticated requests on 2026-10-09; the owner would download chosen files manually in a browser (respecting site terms) and drop them in `bench/.cache/manual/` with the attribution recorded in the manifest. I did not work around the block.
D. **Owner-created stems**: the owner records/produces a few short multitracks (or uses stems they own the rights to). Highest realism for the target genre, clear rights, costs owner time.
E. **Full Slakh2100** (CC BY 4.0, 44.1 kHz flac, ~100 GB). Full-band, many tracks, still MIDI renders and no vocals. Disk is available (711 GB free); download time is the cost.

## Recommendation
**C + D for a small, full-band, genre-relevant holdout (5–10 items), plus E only if instrument-level metrics at 44.1 kHz become a gate.** B is reasonable, but it needs a terms agreement on your behalf, so I have not accepted it.

## Consequences
All options are reversible; no audio is committed to the repo in any option. Options B and C put third-party terms acceptance in the owner's name.

## Decision record (2026-10-09)
**Approved:** expand evaluation with **5–10 full-quality tracks** representative of house, trance, hip-hop and instrumental sampling.

Conditions:
1. Every item's licence/permission is documented in the manifest (source, licence, attribution, who granted permission and when).
2. Real multitrack references are preferred over synthetic mixes.
3. Include 44.1 kHz and 48 kHz material.
4. Evaluate audible artifacts, transients, cymbals, bass, vocal bleed and false vocal extraction (objective metrics where ground truth exists + blinded listening).
5. Prepare a blinded listening evaluation for the expanded set (same rubric as `docs/research/LISTENING_TEST.md`).
6. **The original frozen benchmark is unchanged.** `bench/config/frozen.json` (sha256 `cb98142e…`) and its holdout results are not edited; the expansion gets its own manifest section, split and frozen config.
7. **Not complete until the audio exists and has been evaluated.** No results may be reported for items that have not been acquired and run.
8. No restricted content, no bypassing access controls (e.g. the ccMixter 403 stays a manual, owner-performed download), no terms accepted by the agent on the owner's behalf.

Status of the expansion: **0 of 5–10 items acquired.** Acquisition path per item is the owner's choice (options C/D above; B needs the owner to accept QUASI terms).
