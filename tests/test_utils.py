from i18n_agent_skill.models import ConflictStrategy
from i18n_agent_skill.tools import _deep_update, _flatten_dict, _unflatten_dict


def test_flatten_basic():
    """测试基础字典拍平"""
    nested = {"a": {"b": {"c": "val"}}}
    flat = _flatten_dict(nested)
    assert flat["a.b.c"] == "val"
    assert len(flat) == 1

def test_unflatten_basic():
    """测试字典还原"""
    flat = {"auth.login.title": "Sign In"}
    unflattened = _unflatten_dict(flat)
    assert unflattened["auth"]["login"]["title"] == "Sign In"

def test_deep_update_keep_strategy():
    """测试保留现有策略"""
    base = {"ui": {"btn": "Old"}}
    update = {"ui": {"btn": "New", "icon": "add"}}
    # 策略：KEEP (不覆盖已有内容)
    res = _deep_update(base.copy(), update, ConflictStrategy.KEEP_EXISTING)
    assert res["ui"]["btn"] == "Old"
    assert res["ui"]["icon"] == "add"

def test_deep_update_overwrite_strategy():
    """测试强制覆盖策略"""
    base = {"ui": {"btn": "Old"}}
    update = {"ui": {"btn": "New"}}
    # 策略：OVERWRITE (直接覆盖)
    res = _deep_update(base.copy(), update, ConflictStrategy.OVERWRITE)
    assert res["ui"]["btn"] == "New"
