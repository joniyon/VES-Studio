import numpy as np
import pytest

from app.inversion.forward import schlumberger_forward
from app.processing import WorkingCurveConfig, build_working_curve

RHO, TH = [100.0, 20.0, 300.0], [2.0, 10.0]
# measurement order with repeated spacings at each MN change (5 segments)
AB = np.array([1.5, 2, 3, 5, 6, 6, 8, 12, 15, 15, 25, 32, 40, 40, 50, 65, 80, 100, 100, 120, 150, 200, 200, 250.0])
TRUE = schlumberger_forward(AB, RHO, TH)
from app.processing.working_curve import segment_ids  # noqa: E402


def test_segment_ids_split_at_repeats():
    s = segment_ids(AB)
    # repeats at 6, 15, 40, 100, 200 -> six segments, each new one starting at the repeated spacing
    assert s.max() == 5 and np.all(np.diff(s) >= 0)
    assert s[4] == 0 and s[5] == 1            # first "6" ends segment 1, second "6" starts segment 2


def test_shift_recovers_known_segment_offsets():
    s = segment_ids(AB)
    factors = np.array([1.0, 0.8, 1.25, 0.9, 1.1, 0.7])[: s.max() + 1]
    observed = TRUE * factors[s]
    wc = build_working_curve(AB, observed, cfg=WorkingCurveConfig(overlap="shift", anchor_segment=0))
    np.testing.assert_allclose(wc.shifts, 1.0 / factors, rtol=1e-9)        # each segment's offset is undone
    # merged curve equals the truth at unique spacings (noise-free), up to the anchor's own scale
    truth_unique = schlumberger_forward(wc.spacing, RHO, TH)
    np.testing.assert_allclose(wc.values, truth_unique, rtol=1e-9)
    assert wc.shifts[0] == 1.0 and len(wc.spacing) == len(np.unique(AB))


def test_average_merges_repeats_without_shifting():
    obs = TRUE.copy()
    wc = build_working_curve(AB, obs, cfg=WorkingCurveConfig(overlap="average"))
    assert len(wc.spacing) == len(np.unique(AB)) and wc.shifts == [1.0]
    assert [1 if len(r) > 1 else 0 for r in wc.source_rows].count(1) == 5


def test_none_keeps_everything_sorted():
    wc = build_working_curve(AB, TRUE, cfg=WorkingCurveConfig())
    assert len(wc.spacing) == len(AB) and np.all(np.diff(wc.spacing) >= 0)
    np.testing.assert_allclose(wc.values, TRUE)


def test_median_removes_single_spike_but_keeps_trend():
    sp = np.geomspace(1, 200, 15)
    clean = schlumberger_forward(sp, RHO, TH)
    noisy = clean.copy(); noisy[7] *= 6.0
    wc = build_working_curve(sp, noisy, cfg=WorkingCurveConfig(smooth="median", window=3))
    assert abs(np.log(wc.values[7] / clean[7])) < 0.25          # spike gone
    assert abs(np.log(noisy[7] / clean[7])) > 1.5
    np.testing.assert_allclose(wc.values[3], clean[3], rtol=0.15)


def test_hanning_smooths_and_preserves_monotone_trend():
    sp = np.geomspace(1, 100, 12)
    v = np.exp(np.linspace(0, 3, 12))                            # log-linear ramp: hanning keeps interior exactly
    wc = build_working_curve(sp, v, cfg=WorkingCurveConfig(smooth="hanning", window=5))
    np.testing.assert_allclose(wc.values[2:-2], v[2:-2], rtol=1e-9)


def test_merged_groups_keep_their_raw_rows_and_carry_no_averaged_mn():
    sp = np.array([1.0, 2.0, 2.0, 3.0])
    wc = build_working_curve(sp, [1, 2, 2, 3], cfg=WorkingCurveConfig(overlap="average"))
    assert wc.source_rows == [[0], [1, 2], [3]] and not hasattr(wc, "mn")


def test_errors_and_validation():
    with pytest.raises(ValueError, match="non-decreasing"):
        build_working_curve([1, 3, 2], [1, 1, 1], cfg=WorkingCurveConfig(overlap="shift"))
    with pytest.raises(ValueError, match="does not exist"):
        build_working_curve([1, 2, 2, 3], [1, 2, 2, 3], cfg=WorkingCurveConfig(overlap="shift", anchor_segment=5))
    with pytest.raises(ValueError):
        build_working_curve([1, 2], [1, -2])
    for bad in (dict(overlap="x"), dict(smooth="x"), dict(window=4), dict(anchor_segment=-1)):
        with pytest.raises(ValueError):
            WorkingCurveConfig(**bad)
    wc = build_working_curve([1, 2, 3, 4], [1, 2, 3, 4], cfg=WorkingCurveConfig(overlap="shift"))
    assert wc.shifts == [1.0]


def test_excluding_an_overlap_point_merges_segments_instead_of_shifting():
    # dropping one of a repeated pair removes the repeat, so there is no longer a segment boundary there
    sp = np.delete(AB, 5)
    assert segment_ids(sp).max() == segment_ids(AB).max() - 1
