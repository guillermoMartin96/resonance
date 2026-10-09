# Product specification — StemForge (working title)

## Vision
An approachable creative workstation that lets a user import an audio recording they are authorized to process, separate its **actual audible content**, audition and trim isolated stems, and assemble a new remix from those samples.

## Users
Curious hip-hop and electronic-music samplers who know the vibe they want but not traditional DAW workflows; more advanced creators seeking fast sound discovery.

## Primary workflow
Import authorized WAV/MP3/FLAC → analyze duration/sample rate → run separation → audition solo/mute and A/B against original → mark regions → save named reusable clips with source/provenance → place clips on a simple timeline → preview and export.

## Product priorities
P0: authentic-audio stem extraction, transparent quality and provenance, local upload, playback.
P1: reusable sample library, trimming, timeline, time alignment, WAV export.
P2: deeper drum/percussion isolation, beat/key analysis, compatible sample search, AI conversational editing.
P3: public-library integrations, advanced mixing, optional collaboration and mobile.

## Non-goals for first milestone
Full DAW, perfect single-instrument separation, original studio multitrack recovery, Spotify ripping, MIDI reconstruction, generative sound recreation, video, commercial distribution pipeline.

## Success criteria
User can upload a permitted recording, request separation, hear the output stems and compare them to the original; failures are actionable; sample rights and source metadata remain attached.

## Rights and safety
Require an explicit rights/authorization acknowledgement for uploads; store user-supplied license/source information; do not claim this proves permission. Publicly accessible does not mean public domain. Export must preserve provenance metadata in a sidecar manifest. Avoid embedding copyrighted demo tracks in repo or tests; use synthetic and permissively licensed fixtures.

## Open questions
Target initial max audio duration, offline-only vs local server, acceptable processing time and separation quality, whether commercial export is in scope, and branding/trademark clearance.
