import csv
import importlib.util
import json
from pathlib import Path

import numpy as np

from stemforge_bench.audio import read_audio, write_audio

_spec = importlib.util.spec_from_file_location(
    "make_listening_packet", Path(__file__).resolve().parents[1] / "scripts" / "make_listening_packet.py")
mlp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mlp)

SR = 8000


def _outputs(root: Path, items=("item-1", "item-2")) -> Path:
    rng = np.random.default_rng(0)
    for item in items:
        d = root / item
        mix = (rng.standard_normal((1, SR)) * 0.2).astype(np.float32)
        write_audio(d / "mixture.wav", mix, SR)
        write_audio(d / "sep.loud__vocals.wav", mix, SR)              # mixture anchor, loud
        write_audio(d / "sep.quiet__vocals.wav", mix * 0.05, SR)      # 26 dB quieter
        write_audio(d / "sep.quiet__drums.wav", mix * 0.05, SR)       # other role: ignored
    return root


def test_key_is_outside_packet_and_complete(tmp_path):
    src = _outputs(tmp_path / "outputs")
    dst, key_path = tmp_path / "listening" / "pkt", tmp_path / "keys" / "KEY.json"
    mlp.build_packet(src, dst, key_path, role="vocals", seed=1)
    assert key_path.exists()
    assert not any(p.name.upper().startswith("KEY") for p in dst.rglob("*")), "key leaked into packet"
    assert not key_path.resolve().is_relative_to(dst.resolve())
    key = json.loads(key_path.read_text())
    assert set(key["items"]) == {"item-1", "item-2"}
    for labels in key["items"].values():
        assert sorted(v["separator"] for v in labels.values()) == ["sep.loud", "sep.quiet"]
    assert not any("sep." in p.name for p in dst.rglob("*")), "separator id visible in packet"


def test_candidates_are_loudness_matched(tmp_path):
    src = _outputs(tmp_path / "outputs")
    dst = tmp_path / "pkt"
    mlp.build_packet(src, dst, tmp_path / "KEY.json", role="vocals", seed=1)
    for item in ("item-1", "item-2"):
        levels = []
        for f in sorted((dst / item).glob("[A-Z].wav")):
            x, _ = read_audio(f)
            levels.append(10 * np.log10(np.mean(x.astype(np.float64) ** 2)))
            assert np.abs(x).max() <= 1.0
        assert len(levels) == 2
        assert max(levels) - min(levels) < 0.5, levels


def test_rerun_clears_stale_labels_and_writes_blank_ratings(tmp_path):
    src = _outputs(tmp_path / "outputs")
    dst = tmp_path / "pkt"
    (dst / "item-1").mkdir(parents=True)
    (dst / "item-1" / "Z.wav").write_bytes(b"stale")
    mlp.build_packet(src, dst, tmp_path / "KEY.json", role="vocals", seed=2)
    assert not (dst / "item-1" / "Z.wav").exists()
    rows = list(csv.DictReader((dst / "ratings.csv").open()))
    assert {(r["item"], r["label"]) for r in rows} == {(i, l) for i in ("item-1", "item-2") for l in "AB"}
    assert all(r["isolation"] == "" and r["usable"] == "" for r in rows), "ratings must start blank"


def test_seed_reproducible(tmp_path):
    src = _outputs(tmp_path / "outputs")
    k1, k2 = tmp_path / "k1.json", tmp_path / "k2.json"
    mlp.build_packet(src, tmp_path / "p1", k1, role="vocals", seed=7)
    mlp.build_packet(src, tmp_path / "p2", k2, role="vocals", seed=7)
    assert json.loads(k1.read_text())["items"] == json.loads(k2.read_text())["items"]
