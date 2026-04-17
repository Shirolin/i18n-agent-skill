from i18n_agent_skill.linter import TranslationStyleLinter

# ==========================================
# CJK (zh, ja, ko) tests
# ==========================================

def test_linter_missing_space_cjk_latin_zh():
    """测试中文后紧跟英文缺失空格"""
    feedbacks = TranslationStyleLinter.lint("key1", "确认Email地址", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "MISSING_SPACE_CJK_LATIN"
    assert feedbacks[0].suggestion == "确认 Email 地址"

def test_linter_missing_space_latin_cjk_zh():
    """测试英文后紧跟中文缺失空格"""
    feedbacks = TranslationStyleLinter.lint("key2", "Hello世界", "zh-CN")
    assert len(feedbacks) == 1
    # 注意：我们的新正则两边都会换行补空格，所以这里 violation 是以是否包含 cjk_en 顺序来定。
    # 这里是 en_cjk，按逻辑是 MISSING_SPACE_LATIN_CJK
    assert feedbacks[0].violation == "MISSING_SPACE_LATIN_CJK"
    assert feedbacks[0].suggestion == "Hello 世界"

def test_linter_half_width_punctuation_zh():
    """测试中文语境下误用半角逗号"""
    feedbacks = TranslationStyleLinter.lint("key3", "确认提交,请稍后", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "ILLEGAL_HALF_WIDTH_PUNCTUATION"
    assert "，" in feedbacks[0].suggestion

def test_linter_missing_space_ja():
    """测试日文假名与英文混排空格"""
    feedbacks = TranslationStyleLinter.lint("key_ja", "プロファイルIDを確認", "ja-JP")
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "プロファイル ID を確認"

def test_linter_missing_space_ko():
    """测试韩文音节与数字混排空格"""
    feedbacks = TranslationStyleLinter.lint("key_ko", "사용자123정보", "ko-KR")
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "사용자 123 정보"

def test_linter_correct_cjk_text():
    """测试合规的中日韩文本不触发告警"""
    feedbacks = TranslationStyleLinter.lint("key4", "发送 Email，确认提交。", "zh-CN")
    assert len(feedbacks) == 0


# ==========================================
# Latin (en, es, etc.) tests
# ==========================================

def test_linter_latin_consecutive_spaces():
    """测试西文连续空格"""
    feedbacks = TranslationStyleLinter.lint("key_en_space", "Hello  beautiful   world", "en-US")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "CONSECUTIVE_SPACES"
    assert feedbacks[0].suggestion == "Hello beautiful world"

def test_linter_latin_punctuation_spacing():
    """测试西文标点后缺失空格"""
    feedbacks = TranslationStyleLinter.lint("key_es_punct", "Hola,mundo!¿Qué tal?", "es-ES")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "MISSING_SPACE_AFTER_PUNCTUATION"
    assert feedbacks[0].suggestion == "Hola, mundo!¿Qué tal?" # !后有¿，不是字母，不加空格。o前面是?，后边是Q，加空格：Hola, mundo!¿Qué tal?
    
def test_linter_latin_punctuation_spacing_advanced():
    """测试西文标点后字母缺空格，同时验证数字小数/千分位不受影响"""
    feedbacks = TranslationStyleLinter.lint("key_en_punct2", "Price is 1,234.56,please confirm.", "en-US")
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "Price is 1,234.56, please confirm."

def test_linter_unsupported_lang():
    """测试未配置规则的语言安全放行"""
    # ar (阿拉伯语) 未配置，应该通过不报错
    feedbacks = TranslationStyleLinter.lint("key_ar", "مرحبا  العالم,كيف حالك", "ar-SA")
    assert len(feedbacks) == 0

