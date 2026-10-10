import importlib.util

import numpy as np
import pytest

from stemforge_bench.separators import SeparationError, create
from stemforge_bench.separators.base import validate_output
from stemforge_bench.separators.mdx_onnx import MODEL_DIR

SR = 44100


def _audio(channels=2, seconds=3.0, seed=0):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((channels, int(SR * seconds))) * 0.1).astype(np.float32)


@pytest.mark.parametrize("sid", ["baseline.mixture", "baseline.hpss"])
@pytest.mark.parametrize("channels", [1, 2])
def test_baseline_contract(sid, channels):
    sep = create(sid)
    sep.load()
    x = _audio(channels)
    x0 = x.copy()
    stems = sep.separate(x, SR)
    validate_output(sep.info, x, stems)
    np.testing.assert_array_equal(x, x0)  # input not mutated


def test_hpss_is_near_complete():
    sep = create("baseline.hpss")
    x = _audio()
    s = sep.separate(x, SR)
    recon = s["drums"] + s["bass"] + s["other"]
    assert np.max(np.abs(recon[:, 4096:-4096] - x[:, 4096:-4096])) < 1e-3


def test_rejects_bad_input():
    sep = create("baseline.mixture")
    for bad in (np.zeros((3, 10), np.float32), np.zeros((2, 0), np.float32), np.full((2, 10), np.nan, np.float32)):
        with pytest.raises(SeparationError):
            sep.separate(bad, SR)
    with pytest.raises(SeparationError):
        create("nope")


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch not installed")
def test_numpy_stft_matches_torch():
    import torch
    from stemforge_bench.separators.mdx_onnx import istft, stft
    n_fft, hop = 6144, 1024
    x = _audio(2, 2.0)[:, : hop * 100]
    win = np.hanning(n_fft + 1)[:-1]
    ours = stft(x.astype(np.float64), n_fft, hop, win)
    ref = torch.stft(torch.from_numpy(x.astype(np.float64)), n_fft=n_fft, hop_length=hop,
                     window=torch.hann_window(n_fft, periodic=True, dtype=torch.float64),
                     center=True, return_complex=True).numpy()
    np.testing.assert_allclose(ours, ref, atol=1e-8)
    back = istft(ours, n_fft, hop, win)
    np.testing.assert_allclose(back, x[:, : back.shape[1]], atol=1e-8)


@pytest.mark.slow
@pytest.mark.skipif(not (MODEL_DIR / "Kim_Vocal_2.onnx").exists(), reason="MDX weights not fetched")
def test_mdx_contract():
    sep = create("mdx.Kim_Vocal_2")
    x = _audio(2, 4.0)
    stems = sep.separate(x, SR)
    validate_output(sep.info, x, stems)
    np.testing.assert_allclose(stems["vocals"] * 0 + stems["accompaniment"] + stems["vocals"] * sep._params["compensate"],
                               x, atol=1e-3)


@pytest.mark.slow
@pytest.mark.skipif(importlib.util.find_spec("demucs") is None, reason="demucs not installed")
def test_demucs_contract():
    sep = create("demucs.htdemucs")
    x = _audio(1, 4.0)
    stems = sep.separate(x, SR)
    validate_output(sep.info, x, stems)
    assert sep.info.weights_sha256, "weights should be hashed for provenance"
