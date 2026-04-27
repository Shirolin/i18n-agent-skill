from i18n_agent_skill.models import ConflictStrategy
from i18n_agent_skill.tools import _deep_update, _flatten_dict, _unflatten_dict


def test_flatten_dict():
    """Test basic dictionary flattening."""
    d = {"a": {"b": {"c": "val"}}, "d": "val2"}
    res = _flatten_dict(d)
    assert res == {"a.b.c": "val", "d": "val2"}


def test_unflatten_dict():
    """Test dictionary unflattening."""
    d = {"a.b.c": "val", "d": "val2"}
    res = _unflatten_dict(d)
    assert res == {"a": {"b": {"c": "val"}}, "d": "val2"}


def test_deep_update_keep_existing():
    """Test keeping existing values strategy."""
    base = {"a": 1, "b": {"c": 2}}
    update = {"a": 10, "b": {"c": 20, "d": 3}}
    # Strategy: KEEP (do not overwrite existing)
    res = _deep_update(base.copy(), update, ConflictStrategy.KEEP_EXISTING)
    assert res["a"] == 1
    assert res["b"]["c"] == 2
    assert res["b"]["d"] == 3


def test_deep_update_overwrite():
    """Test force overwrite strategy."""
    base = {"a": 1, "b": {"c": 2}}
    update = {"a": 10, "b": {"c": 20, "d": 3}}
    # Strategy: OVERWRITE
    res = _deep_update(base.copy(), update, ConflictStrategy.OVERWRITE)
    assert res["a"] == 10
    assert res["b"]["c"] == 20
    assert res["b"]["d"] == 3
