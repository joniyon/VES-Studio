import pytest

from app.interpretation import BY_ID, CATALOGUE, get_lithology, suggest


def test_catalogue_integrity():
    assert len({l.id for l in CATALOGUE}) == len(CATALOGUE)
    for l in CATALOGUE:
        assert l.rho_min < l.rho_max and l.color.startswith("#") and len(l.color) == 7
        assert not l.verified, "ranges stay unverified until checked against primary tables"
    assert BY_ID["unclassified"].hatch == ""
    # no two lithologies share the same colour+hatch (columns must stay distinguishable)
    assert len({(l.color, l.hatch) for l in CATALOGUE}) == len(CATALOGUE)


def test_suggestions_are_ranked_candidates_not_single_answers():
    s = suggest(20.0, 2.0, 12.0, max_n=8)
    assert len(s) > 1
    ids = [x.lithology.id for x in s]
    assert "clay" in ids and "weathered_basement" in ids
    assert all("Ωm" in x.basis for x in s)
    assert s[0].score <= s[-1].score


def test_depth_plausibility_penalises_surface_material_at_depth():
    deep = {x.lithology.id: x for x in suggest(300.0, 40.0, None, max_n=20)}
    shallow = {x.lithology.id: x for x in suggest(300.0, 0.0, 1.0, max_n=20)}
    assert not deep["laterite"].depth_ok and shallow["laterite"].depth_ok
    assert deep["laterite"].score > shallow["laterite"].score


def test_very_high_resistivity_points_to_crystalline():
    assert suggest(5000.0, 15.0, None)[0].lithology.id in {"fresh_basement", "limestone", "volcanic", "sandstone"}


def test_bad_input():
    with pytest.raises(ValueError):
        suggest(-1.0, 0.0, 1.0)
    with pytest.raises(ValueError):
        get_lithology("nope")
