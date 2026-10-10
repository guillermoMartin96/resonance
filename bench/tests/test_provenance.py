"""Artifact verification, frozen-config binding and reproducibility (review M0-01..06)."""
import hashlib
import importlib.util
import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pytest

from stemforge_bench import platform_info
from stemforge_bench.separators import SeparationError, create
from stemforge_bench.separators import mdx_onnx

BENCH = Path(__file__).resolve().parents[1]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --- M0-01: MDX weights and UVR parameter table verified before use -----------------

def test_mdx_rejects_unpinned_or_tampered_weights(tmp_path, monkeypatch):
    (tmp_path / "Kim_Vocal_2.onnx").write_bytes(b"not the real model")
    (tmp_path / "model_data.json").write_bytes(b"{}")
    sep = mdx_onnx.MDXOnnxSeparator("Kim_Vocal_2.onnx", model_dir=tmp_path)
    with pytest.raises(SeparationError, match="sha256"):
        sep.load()


def test_mdx_rejects_tampered_param_table(tmp_path, monkeypatch):
    weights = b"fake weights"
    (tmp_path / "Kim_Vocal_2.onnx").write_bytes(weights)
    (tmp_path / "model_data.json").write_bytes(b'{"tampered": true}')
    monkeypatch.setitem(mdx_onnx.MODEL_SHA256, "Kim_Vocal_2.onnx", _sha(weights))
    sep = mdx_onnx.MDXOnnxSeparator("Kim_Vocal_2.onnx", model_dir=tmp_path)
    with pytest.raises(SeparationError, match="model_data.json"):
        sep.load()


def test_mdx_param_table_url_is_pinned_to_a_commit():
    assert "/main/" not in mdx_onnx.PARAMS_URL
    assert len(mdx_onnx.PARAMS_REVISION) == 40


# --- M0-02: Demucs files pinned by revision and sha256, verified before loading ------

def test_demucs_pins_revision_and_every_file():
    from stemforge_bench.separators.demucs_adapter import PINNED
    for name in ("htdemucs", "htdemucs_ft"):
        pin = PINNED[name]
        assert len(pin["revision"]) == 40
        assert f"{name}.yaml" in pin["files"]
        assert any(f.endswith(".safetensors") for f in pin["files"])


def test_demucs_rejects_tampered_file_before_loading(tmp_path):
    from stemforge_bench.separators.demucs_adapter import resolve_pinned_files
    calls = []

    def fake_download(repo_id, filename, revision):
        calls.append((repo_id, filename, revision))
        p = tmp_path / filename
        p.write_bytes(b"tampered")
        return str(p)

    with pytest.raises(SeparationError, match="sha256"):
        resolve_pinned_files("htdemucs", download=fake_download)
    assert calls and all(rev == calls[0][2] and len(rev) == 40 for _, _, rev in calls)


def test_demucs_unpinned_model_refused():
    from stemforge_bench.separators.demucs_adapter import resolve_pinned_files
    with pytest.raises(SeparationError, match="not pinned"):
        resolve_pinned_files("mdx_extra", download=lambda *a, **k: "")


# --- M0-04: Demucs seed controls the shift RNG ----------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(importlib.util.find_spec("demucs") is None, reason="demucs not installed")
def test_demucs_repeatable_with_same_seed():
    import random
    rng = np.random.default_rng(3)
    x = (rng.standard_normal((2, 44100 * 4)) * 0.1).astype(np.float32)
    sep = create("demucs.htdemucs")
    random.seed(12345)
    a = sep.separate(x, 44100)
    random.seed(999)                       # global state must not matter...
    b = sep.separate(x, 44100)
    for role in a:
        np.testing.assert_array_equal(a[role], b[role])
    state = random.getstate()
    sep.separate(x, 44100)
    assert random.getstate() == state      # ...and must not be clobbered


# --- M0-03: frozen config is applied and validated, inputs are hashed -----------------

def _frozen():
    return json.loads((BENCH / "config" / "frozen.json").read_text())


def test_committed_frozen_config_matches_code():
    from stemforge_bench.run import check_frozen
    cfg = _frozen()
    for ds in ("procedural", "babyslakh", "vocalmix"):
        for sid in cfg["separators"]:
            if sid.startswith("baseline."):
                check_frozen(cfg, ds, create(sid))  # must not raise


@pytest.mark.parametrize("mutate", [
    lambda c: c["datasets"]["procedural"].update(holdout_seeds=[9999]),
    lambda c: c["datasets"]["procedural"].update(seconds=1),
    lambda c: c["datasets"]["babyslakh"].update(excerpt_s=10),
    lambda c: c["datasets"]["vocalmix"].update(pairs_per_vocal=3),
    lambda c: c["separators"]["baseline.hpss"].update(kernel=31),
    lambda c: c["separators"]["baseline.hpss"].update(unknown_param=1),
])
def test_frozen_config_mismatch_rejected(mutate):
    from stemforge_bench.run import check_frozen
    cfg = _frozen()
    mutate(cfg)
    with pytest.raises(ValueError):
        for d in ("procedural", "babyslakh", "vocalmix"):
            check_frozen(cfg, d, create("baseline.hpss"))


def test_item_digest_changes_with_content():
    from stemforge_bench.datasets import procedural
    from stemforge_bench.run import item_digest
    a, b = procedural.make_item(0, seconds=16), procedural.make_item(0, seconds=16)
    assert item_digest(a) == item_digest(b)
    b.stems["bass"][0, 100] += 1e-3
    assert item_digest(a) != item_digest(b)


# --- M0-05: platform-aware RSS --------------------------------------------------------

def test_rss_units(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert platform_info.maxrss_to_mb(2_000_000) == pytest.approx(2.0)      # bytes
    monkeypatch.setattr(sys, "platform", "linux")
    assert platform_info.maxrss_to_mb(2_000) == pytest.approx(2.0)          # KiB


def test_perf_probe_uses_platform_aware_rss():
    src = (BENCH / "scripts" / "perf_probe.py").read_text()
    assert "/ 1e6" not in src and "platform_info" in src


# --- M0-06: model downloads are atomic and self-healing -------------------------------

def _load_fetch_models():
    spec = importlib.util.spec_from_file_location("fetch_models", BENCH / "scripts" / "fetch_models.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_interrupted_leaves_no_destination(tmp_path, monkeypatch):
    fm = _load_fetch_models()

    class Broken(_Resp):
        def read(self, *a):
            raise ConnectionResetError("dropped")

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Broken(b""))
    dest = tmp_path / "m.onnx"
    with pytest.raises(ConnectionResetError):
        fm.fetch("https://example.invalid/m.onnx", dest, _sha(b"good"))
    assert not dest.exists()


def test_fetch_replaces_corrupt_cache_and_verifies(tmp_path, monkeypatch):
    fm = _load_fetch_models()
    dest = tmp_path / "m.onnx"
    dest.write_bytes(b"partial")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp(b"good"))
    fm.fetch("https://example.invalid/m.onnx", dest, _sha(b"good"))
    assert dest.read_bytes() == b"good"
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp(b"evil"))
    dest.unlink()
    with pytest.raises(fm.ChecksumError):
        fm.fetch("https://example.invalid/m.onnx", dest, _sha(b"good"))
    assert not dest.exists()
