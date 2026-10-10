import numpy as np
import pytest

from stemforge_bench.metrics import decompose, evaluate_stem, sdr, si_sdr, silent_leak_db


def _refs(n=44100 * 3, seed=0):
    rng = np.random.default_rng(seed)
    return {k: rng.standard_normal((2, n)).astype(np.float32) * 0.1 for k in ("vocals", "drums", "bass", "other")}


def test_sdr_perfect_and_scaled():
    refs = _refs()
    r = refs["drums"]
    assert sdr(r, r) > 90
    assert si_sdr(r, 0.5 * r) > 90          # scale invariant
    assert sdr(r, 0.5 * r) == pytest.approx(6.02, abs=0.05)  # 20log10(1/0.5)


def test_mixture_estimate_has_expected_sdr():
    refs = _refs()
    mix = sum(refs.values())
    # independent equal-power sources: target is 1/4 of mixture energy -> SDR ~ -4.77 dB
    assert sdr(refs["vocals"], mix) == pytest.approx(-4.77, abs=0.2)


def test_decompose_bleed_and_artifacts():
    refs = _refs()
    est = refs["vocals"] + 0.1 * refs["drums"]
    d = decompose(refs, "vocals", est)
    assert d["sir"] == pytest.approx(20.0, abs=0.3)
    assert d["sar"] > 60
    assert d["bleed_ratio"] == pytest.approx(0.0099, abs=0.002)
    noisy = refs["vocals"] + 0.1 * np.random.default_rng(9).standard_normal(est.shape).astype(np.float32) * 0.1
    assert decompose(refs, "vocals", noisy)["sar"] == pytest.approx(20.0, abs=0.5)


def test_accompaniment_group():
    refs = _refs()
    acc = refs["drums"] + refs["bass"] + refs["other"]
    m = evaluate_stem(refs, sum(refs.values()), "accompaniment", acc, 44100)
    assert m["sdr"] > 90 and m["sir"] > 60


def test_silent_leak():
    sr = 1000
    ref = np.zeros((1, 10 * sr), np.float32); ref[:, : 5 * sr] = 1
    mix = np.ones((1, 10 * sr), np.float32)
    est = ref.copy(); est[:, 5 * sr:] = 0.1
    assert silent_leak_db(ref, est, mix, sr) == pytest.approx(-20.0, abs=0.1)
    assert silent_leak_db(ref, ref, mix, sr) < -90
    assert silent_leak_db(mix, mix, mix, sr) is None   # target never silent
