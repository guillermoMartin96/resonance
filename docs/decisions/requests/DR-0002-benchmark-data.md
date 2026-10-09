# DR-0002 — Benchmark corpus expansion (real multitrack material)

Status: OPEN — owner approval needed. M0 proceeded with the sources below that needed no account, form or terms acceptance.

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

## Approval
Owner selects options. No terms will be accepted and no account-gated downloads made by the agent.
