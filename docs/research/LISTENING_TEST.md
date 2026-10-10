# M0 blind listening test — owner instructions

**Status: PENDING — packet generated and verified; no ratings submitted.** The agent has not listened to anything and has not opened the key. Nothing below is a result.

Time needed: about 20–30 minutes. Use headphones or monitors you know, in a quiet room, at a fixed comfortable volume (don't change it mid-test).

## What you're rating
4 dev items from the `vocalmix` benchmark: a real recorded vocal (Wikimedia Commons, CC0 / US-Gov PD) mixed over a BabySlakh accompaniment. Mono, 16 kHz, 30 s. Each item folder has:

- `mixture.wav`: the input, for orientation. Not rated.
- `A.wav` … `E.wav`: five **vocal** estimates, one per engine, in a random order that differs per item. All are matched to the same loudness (−23 dBFS RMS), so level differences aren't a clue.

One of the five is the unprocessed mixture (the "no separation" anchor). It will sound obviously bad; that's intended. It checks that the scale is being used, so rate it honestly too.

Limits to keep in mind: 16 kHz material can't reveal cymbal or air-band artifacts above 8 kHz, and the vocal and backing aren't musically related. This test covers isolation, integrity and artifacts in the vocal band only. Full-band genre material is the DR-0002 follow-up.

## Steps
1. **Generate a fresh packet** (or reuse the one already generated on 2026-10-09). From the repo root, in the `feature/m0-research` worktree:
   ```bash
   cd bench
   .venv/bin/python scripts/make_listening_packet.py --dataset vocalmix --split dev --role vocals
   ```
   The packet goes to `bench/.cache/listening/vocalmix/dev/vocals/`. The key goes to `bench/.cache/listening_keys/…/KEY.json`. **Don't open the key, or the `outputs/` folder (its file names reveal the engines), until step 4.**
   If the saved outputs are missing (fresh clone), first run, for each of `baseline.mixture demucs.htdemucs demucs.htdemucs_ft mdx.Kim_Vocal_2 mdx.UVR-MDX-NET-Inst_HQ_3`:
   `.venv/bin/python -m stemforge_bench.run --dataset vocalmix --split dev --separator <id> --save-audio --out /tmp/ignore`
   (`--out` elsewhere so the committed result JSONs are not overwritten).
2. **Listen and rate.** For each item, play `mixture.wav` once, then each letter as many times as you like. Fill one row per item × letter in `ratings.csv` (open it in any spreadsheet app and save it as CSV):

   | column | scale | meaning |
   |---|---|---|
   | `isolation` | 1–5 | how little of the backing (drums, bass, keys) is audible. 5 = none |
   | `integrity` | 1–5 | the vocal is intact: consonants, breaths, tails, reverb. 5 = nothing missing |
   | `artifacts` | 1–5 | phasiness / "underwater", warbling, metallic or musical noise, pumping. 5 = none |
   | `usable` | yes/no | "Would I chop and use a region of this in a track?" |
   | `failure_timestamps` | free text | e.g. `0:12 drum bleed; 0:21 vocal drops out` |
   | `notes` | free text | anything else |

   Rate the letters within an item against each other. Don't try to keep scores consistent across items.
3. **Freeze your ratings before unblinding.** Copy the filled sheet into the repo:
   ```bash
   mkdir -p docs/research/listening
   cp bench/.cache/listening/vocalmix/dev/vocals/ratings.csv docs/research/listening/M0-vocalmix-dev-vocals-ratings.csv
   git add docs/research/listening && git commit -m "M0 listening: owner ratings (blind)"
   ```
   This commit is the evidence that the ratings were written down before you saw the key.
4. **Unblind.** Copy `bench/.cache/listening_keys/vocalmix/dev/vocals/KEY.json` to `docs/research/listening/M0-vocalmix-dev-vocals-KEY.json` and commit it separately. Then tell the agent "listening results submitted". It will join ratings with the key, summarise per engine, add the table to `M0-separator-evaluation.md`, and mark the gate in `RESEARCH_GATES.md`. It will not change your scores.

## What the result can and cannot change
- It can confirm or challenge the provisional DR-0001 choice (htdemucs default 4-stem, Kim_Vocal_2 optional vocals). For example, if `Kim_Vocal_2` is consistently less usable than `htdemucs`, the "enhanced vocal" option needs revisiting.
- With 4 items and one listener it is **directional, not statistically conclusive**. Treat it as such.
- It does not settle full-band artifacts, cymbals or genre fit. Those wait for the DR-0002 corpus.
