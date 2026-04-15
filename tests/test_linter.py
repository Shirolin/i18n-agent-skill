import pytest
from i18n_agent_skill.linter import TranslationStyleLinter

def test_linter_missing_space_zh_en():
    """测试中文后紧跟英文缺失空格"""
    feedbacks = TranslationStyleLinter.lint("key1", "确认Email地址", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "MISSING_SPACE_ZH_EN"
    assert feedbacks[0].suggestion == "确认 Email 地址"

def test_linter_missing_space_en_zh():
    """测试英文后紧跟中文缺失空格"""
    feedbacks = TranslationStyleLinter.lint("key2", "Hello世界", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "MISSING_SPACE_EN_ZH"
    assert feedbacks[0].suggestion == "Hello 世界"

def test_linter_half_width_punctuation():
    """测试中文语境下误用半角逗号"""
    feedbacks = TranslationStyleLinter.lint("key3", "确认提交,请稍后", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "ILLEGAL_HALF_WIDTH_PUNCTUATION"
    assert "，" in feedbacks[0].suggestion

def test_linter_correct_text():
    """测试合规文本不触发告警"""
    feedbacks = TranslationStyleLinter.lint("key4", "发送 Email，确认提交。", "zh-CN")
    assert len(feedbacks) == 0

def test_linter_non_zh_lang():
    """测试非中文语言不触发风格校验"""
    feedbacks = TranslationStyleLinter.lint("key5", "ConfirmEmail", "en")
    assert len(feedbacks) == 0
