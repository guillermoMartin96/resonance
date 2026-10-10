import numpy as np

from stemforge_bench.datasets import procedural


def test_procedural_deterministic_and_well_formed():
    a, b = procedural.make_item(0, seconds=16), procedural.make_item(0, seconds=16)
    for k in ("vocals", "drums", "bass", "other"):
        assert a.stems[k].shape == (2, 16 * procedural.SR)
        assert a.stems[k].dtype == np.float32
        np.testing.assert_array_equal(a.stems[k], b.stems[k])
        assert np.abs(a.stems[k]).max() > 1e-3, f"{k} silent"
    assert np.abs(a.mixture).max() <= 0.8 + 1e-6


def test_splits_disjoint():
    assert not set(procedural.DEV_SEEDS) & set(procedural.HOLDOUT_SEEDS)
    from stemforge_bench.datasets import slakh
    assert not set(slakh.DEV) & set(slakh.HOLDOUT)


def test_each_stem_has_a_silent_bar():
    item = procedural.make_item(1)
    win = procedural.SR
    for k, v in item.stems.items():
        e = np.sum(v[:, : v.shape[1] // win * win].reshape(2, -1, win) ** 2, axis=(0, 2))
        assert (e < e.max() * 1e-5).any(), f"{k} has no silent second"


def test_manifest_splits_disjoint_and_licensed():
    import json
    from stemforge_bench.datasets.vocalmix import MANIFEST
    m = json.loads(MANIFEST.read_text())
    dev = {a["id"] for a in m["acappellas"] if a["split"] == "dev"}
    hold = {a["id"] for a in m["acappellas"] if a["split"] == "holdout"}
    assert dev and hold and not dev & hold
    for a in m["acappellas"]:
        assert a["license"] and a["attribution"] and a["sha1"]
        assert "NC" not in a["license"], "non-commercial sources are excluded"
