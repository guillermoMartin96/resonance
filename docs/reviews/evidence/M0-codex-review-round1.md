<!-- Verbatim final message of: codex exec -s read-only (codex-cli 0.162.0), reviewing fe8a8f7c261bf37933aabb152b847b030334cf96, 2026-10-09. Brief: docs/reviews/M0-review-handoff.md. Not edited. -->

## Commands run

All checks targeted HEAD `fe8a8f7c261bf37933aabb152b847b030334cf96`. No files were modified or artefacts downloaded.

- `git status --short`; `git rev-parse HEAD` — clean worktree; HEAD matches the requested commit.
- `rg --files` and `find .. -name AGENTS.md -print` — inventoried review files; no repository `AGENTS.md` found.
- `cat`, `sed`, and `nl -ba` on the handoff, implementation, tests, configuration, manifests, workflow, research documents and decision records — inspected the requested scope.
- `git diff --stat 681ae1d..HEAD` — confirmed the change scope.
- `git log --format='%h %ai %s' 681ae1d..HEAD`; `git log -p 681ae1d..HEAD -- bench/config bench/data bench/stemforge_bench/datasets` — inspected freeze and split history.
- `git show --stat e26d6d2`; `git diff cf9af90..e26d6d2 -- bench/stemforge_bench/datasets`; `git diff e26d6d2..HEAD -- bench/config bench/data bench/stemforge_bench/datasets bench/stemforge_bench/separators bench/stemforge_bench/metrics.py` — freeze commit adds configuration; these implementation files remain unchanged afterward.
- `cd bench && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — failed before collection because file capture requires a writable temporary directory.
- Same pytest command with `-s` — **18 passed, 4 errors**; all four errors are listening-packet fixtures requiring temporary directories.
- `rg` and source reads of installed Demucs `apply.py`, `pretrained.py`, `repo.py`, and `hf.py` — verified shift RNG and model-loading behavior.
- `rg --files --hidden … -g mdx_separator.py -g stft.py` — no local reference MDX implementation found in searched locations.
- Attempted Python heredoc — shell rejected temporary-file creation; subsequent probes used quoted `python -c` scripts.
- Read-only Python result/metric probe — recomputed holdout medians and a procedural sample; verified 36 runs and 144 holdout item scores.
- Read-only Python summary/config probe, intercepting filesystem writes — summary matches byte-for-byte; demonstrated acceptance of contradictory frozen settings.
- Offline Python checksum/data/Demucs probe — verified cached source and ONNX hashes, checked split overlap, recomputed real-audio SDR, and demonstrated nondeterministic Demucs output.
- Python listening/MDX probe — inspected existing packet levels without opening its key; tested both MDX models on mono 16 kHz input.
- `git diff --check 681ae1d..HEAD` — three trailing blank-line warnings only.
- Final `git status --short` — clean.

## Findings

### [M0-01] [High] UVR inference parameters are downloaded and used without checksum verification

**Location:** `bench/scripts/fetch_models.py:34`; `bench/stemforge_bench/separators/mdx_onnx.py:99`.

**Evidence:** `model_data.json` is fetched from a mutable `main` URL. Only the two ONNX files have expected SHA-256 values. The adapter directly reads the table and uses its FFT dimensions, primary-stem assignment and compensation factor. The cached table hashes to `1aca8f9bcc57233bc714029663a9ec2345d9c7721f91e5e08f46392a879c6a9a`, but no expected table hash or upstream revision is pinned.

**Impact:** An unverified artefact controls the evaluated signal-processing algorithm. Identical ONNX hashes and frozen-config hashes do not guarantee identical outputs.

**Recommended fix:** Pin the parameter-table revision and SHA-256, verify it before parsing, and record its hash in results. Verify ONNX hashes in the loader before constructing the inference session, rather than relying on a previously executed fetch script.

### [M0-02] [High] Demucs weights are hashed after loading, without enforcing expected weights

**Location:** `bench/stemforge_bench/separators/demucs_adapter.py:50–60`.

**Evidence:** `get_model(self.model_name)` loads the model before `_weight_hashes()` runs. No expected hash or HF revision is supplied. Installed Demucs resolves its YAML and safetensors through unpinned `hf_hub_download` calls. `_weight_hashes()` scans **all snapshots** in a hardcoded cache directory, rather than identifying the files actually loaded; it also omits the bag YAML that controls model composition and weighting.

**Impact:** Recorded hashes do not enforce reproducible model selection or satisfy DR-0001’s requirement for checksums verified before use. Multiple snapshots or a different HF cache location can make provenance misleading or empty.

**Recommended fix:** Pin the HF revision, verify the selected YAML and weight files against expected hashes before loading, and record exactly those resolved files.

### [M0-03] [Medium] Frozen configuration does not bind the executed benchmark

**Location:** `bench/stemforge_bench/run.py:55–71`; `bench/config/frozen.json:4–17`.

**Evidence:** The holdout gate checks only file existence and separator membership, then hashes the file. Separator construction and dataset loading ignore its settings. In an in-memory probe, a config specifying seed `9999`, duration `1`, and an unsupported separator parameter was accepted with return code `0`; the recorded run instead used `procedural-1000`, duration `16`, and parameters `{}`.

Results also lack input-content hashes or a source-content digest. Some procedural results record baseline commit `681ae1d`, which predates this implementation.

**Impact:** The stored frozen hash proves which JSON was supplied, not that its settings, code or data ran. I found no committed post-freeze tuning; this is an enforcement and provenance gap.

**Recommended fix:** Apply or explicitly validate every frozen setting, record dataset/input hashes and implementation identity, and reject unexplained dirty source changes.

### [M0-04] [Medium] Demucs seed does not seed the RNG used for shifts

**Location:** `bench/stemforge_bench/separators/demucs_adapter.py:74`.

**Evidence:** The adapter calls `torch.manual_seed(0)`, but installed `demucs/apply.py:245` selects offsets with Python’s `random.randint`. Two calls on identical input with the same adapter recorded offsets **635** and **6192**. Maximum absolute output differences included **0.07539** for `other` and **0.10389** for `accompaniment`.

**Impact:** The documented seed does not reproduce Demucs estimates or scores. The current tests exercise a contract once and miss this defect.

**Recommended fix:** Seed Python’s RNG for inference, preferably saving and restoring its state, and add a repeated-output reproducibility check. Re-evaluate affected scores before treating small differences as meaningful.

### [M0-05] [Medium] Performance probe reports Linux memory 1,000 times too small

**Location:** `bench/scripts/perf_probe.py:23–29`.

**Evidence:** Every RSS conversion divides `ru_maxrss` by `1e6`. macOS reports bytes; Linux reports KiB. `run.py` correctly handles this distinction, but the probe does not.

**Impact:** Linux execution produces materially incorrect memory evidence. Existing macOS measurements are unaffected.

**Recommended fix:** Use the platform-aware conversion from `run.py` for all probe RSS fields.

### [M0-06] [Low] Interrupted model downloads leave persistent invalid cache files

**Location:** `bench/scripts/fetch_models.py:24–30`.

**Evidence:** Downloads write directly to the final destination. If reading or writing fails after file creation, a partial file remains. Subsequent calls return immediately whenever that destination exists. Weight verification then repeatedly fails; a partial parameter table reaches JSON parsing.

**Impact:** Retrying the documented command cannot repair this cache state without manual deletion.

**Recommended fix:** Download to a temporary sibling, verify it, then rename atomically. Remove or replace invalid cached destinations.

## Verified OK

- **Committed split discipline:** Dataset assignments and implementation were present before freeze commit `e26d6d2` and remain unchanged afterward. Dev/holdout seeds, track IDs and vocal IDs are disjoint. Vocalmix selects accompaniment from its own split.
- **Cached split content:** SHA-256 comparison found **zero identical BabySlakh stem files across dev and holdout**. All five vocal files match their distinct manifest SHA-1 and recorded SHA-256 values.
- **Cached artefacts:** BabySlakh archive MD5 matches `311096dc2bde7d61c97e930edbfc7f78`. Both ONNX SHA-256 values match their pins.
- **Holdout accounting:** All 18 holdout results carry the current frozen hash `cb98142e…`; their item counts total **144**. Loading BabySlakh reproduces **14** holdout items and excludes Track00017.
- **Metrics and aggregation:** SDR, scale-invariant projection, silent-reference `None` handling and silent-window tests passed. Recomputing every metric for procedural item 1000’s mixture baseline produced **zero difference** from JSON. Real Track00006 baseline SDR exactly reproduced **−6.721447** drums, **−6.722338** bass and **2.684235** other.
- **Reported numbers:** Recomputed holdout medians match the evaluation, proof and DR-0001: vocal SDR **11.9190 / 11.7241 / 10.5093 / 10.3097** for Kim / Inst / Demucs-ft / Demucs. Generated `SUMMARY.md` matches byte-for-byte, including median/mean aggregation and exclusion of `None` values.
- **Signal-processing checks:** NumPy STFT/ISTFT parity test passed at its `1e-8` tolerance. HPSS reconstruction and baseline contracts passed. Both MDX models passed mono 16 kHz output contracts; compensation factors are **1.009** and **1.022**.
- **Listening packet:** Existing packet has five anonymous candidates per item; maximum within-item RMS spread is **0.000242 dB**. Code independently shuffles labels, keeps the key outside the packet, and writes blank ratings. I did not open the key.
- **Download/extraction basics:** Audio downloads use `.part` files; manifest checks occur before archive extraction. Extraction uses `filter="data"`. Reviewed subprocess calls use argument lists without shell interpolation.
- **Decision boundaries:** DR-0001 distinguishes code licences from weight rights and requires opt-in ML/non-commercial restrictions. DR-0002 explicitly reports zero expanded-corpus items. Pending listening and expanded-corpus evidence are disclosed.

## Not verified

- Full MDX parity against UVR/python-audio-separator, including the claimed reference-normalisation bug and **47.7/73.6 dB** parity evidence: the throwaway reference environment and reproducible parity script are absent.
- Independent legal verification of upstream licences, attribution obligations and weight-use permissions; no external sources were accessed.
- A Linux CI run or fresh dependency installation.
- Listening-packet generation tests: all four require writes unavailable in this sandbox.
- Full reruns of every ML benchmark and the three-minute performance probe.
- Whether holdout was scored exactly once, or whether uncommitted experiments occurred before the recorded results. Git history supports unchanged committed settings but cannot establish that execution history.
- Broader audio-decoder security or resource-exhaustion resistance. Downloads and decoding have no explicit size/duration limits; I did not establish an exploitable defect.

## Verdict

**Blocking findings: M0-01 and M0-02.**

M0 is **not fit to merge as-is**. It can be fit to merge as provisional research after artefact verification is enforced and affected evidence is validated. Fix the seed and frozen-config gaps before claiming reproducibility. The checked aggregation supports the published numbers; this review does not establish that the engine ranking is wrong.