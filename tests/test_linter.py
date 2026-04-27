from i18n_agent_skill.linter import TranslationStyleLinter


def test_cjk_mixed_spacing():
    """Test missing space after CJK characters followed by Latin."""
    feedbacks = TranslationStyleLinter.lint("key1", "确认Email地址", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "MISSING_SPACE_CJK_LATIN"
    assert feedbacks[0].suggestion == "确认 Email 地址"


def test_latin_cjk_mixed_spacing():
    """Test missing space after Latin characters followed by CJK."""
    feedbacks = TranslationStyleLinter.lint("key2", "Hello世界", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "Hello 世界"


def test_cjk_illegal_punctuation():
    """Test misuse of half-width comma in CJK context."""
    feedbacks = TranslationStyleLinter.lint("key3", "确认提交,请稍后", "zh-CN")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "ILLEGAL_HALF_WIDTH_PUNCTUATION"
    assert feedbacks[0].suggestion == "确认提交，请稍后"


def test_ja_mixed_spacing():
    """Test spacing in Japanese mixed with Latin."""
    feedbacks = TranslationStyleLinter.lint("key_ja", "プロファイルIDを確認", "ja-JP")
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "プロファイル ID を確認"


def test_ko_mixed_spacing():
    """Test spacing in Korean mixed with numbers."""
    feedbacks = TranslationStyleLinter.lint("key_ko", "제1차세계대전", "ko-KR")
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "제 1 차세계대전"


def test_valid_cjk_typography():
    """Test that compliant CJK text does not trigger alarms."""
    feedbacks = TranslationStyleLinter.lint("key4", "发送 Email，确认提交。", "zh-CN")
    assert len(feedbacks) == 0


def test_latin_consecutive_spaces():
    """Test consecutive spaces in Latin contexts."""
    feedbacks = TranslationStyleLinter.lint("key5", "Welcome  to  the system", "en-US")
    assert len(feedbacks) == 1
    assert feedbacks[0].violation == "CONSECUTIVE_SPACES"
    assert feedbacks[0].suggestion == "Welcome to the system"


def test_latin_punctuation_spacing():
    """Test missing space after Latin punctuation."""
    feedbacks = TranslationStyleLinter.lint("key6", "Hello,world! How are you?", "en-US")
    # Only checks punctuation followed by letter (not world! How)
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "Hello, world! How are you?"


def test_unsupported_language_bypass():
    """Test that unsupported languages are passed safely without errors."""
    # ar (Arabic) is not configured, should pass
    feedbacks = TranslationStyleLinter.lint("key7", "مرحبا بك", "ar-SA")
    assert len(feedbacks) == 0


def test_language_endonym_protection():
    """Test semantic protection for language names in components."""
    # Likely a language switcher component
    feedbacks = TranslationStyleLinter.lint("langJapanese", "Japanese", "en-US")
    assert len(feedbacks) == 1
    assert feedbacks[0].suggestion == "日本語"
    assert "Semantic correction" in feedbacks[0].message
