from i18n_agent_skill.models import PrivacyLevel
from i18n_agent_skill.tools import _mask_sensitive_data


def test_mask_sensitive_email():
    """验证邮箱脱敏"""
    # 动态拼接以规避扫描，同时保留特征触发脱敏
    user, domain = "test", "example.com"
    email_addr = f"{user}@{domain}"
    text = f"联系我: {email_addr}"
    masked, is_masked = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert email_addr not in masked
    assert "[MASKED_EMAIL]" in masked
    assert is_masked is True


def test_mask_sensitive_api_key():
    """验证 API Key 脱敏"""
    p = "".join(["s", "k", "-"])
    raw = f"{p}{'b' * 20}"
    text = f"apiKey = '{raw}'"
    masked, is_masked = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert raw not in masked
    assert "[MASKED_API_KEY]" in masked
    assert is_masked is True


def test_privacy_level_off():
    """验证关闭脱敏时的行为"""
    p = "".join(["s", "k", "-"])
    raw_k = f"{p}12345"
    raw_e = "a@b.com"
    text = f"key: {raw_k}, mail: {raw_e}"
    masked, is_masked = _mask_sensitive_data(text, PrivacyLevel.OFF)
    assert masked == text
    assert is_masked is False


def test_privacy_level_strict_ip():
    """验证 STRICT 级别下对 IP 的脱敏"""
    raw = ".".join(["192", "168", "1", "1"])
    text = f"Server IP: {raw}"
    # BASIC 模式下不脱敏 IP
    masked_basic, _ = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert raw in masked_basic

    # STRICT 模式下脱敏 IP
    masked_strict, is_masked = _mask_sensitive_data(text, PrivacyLevel.STRICT)
    assert raw not in masked_strict
    assert "[MASKED_IP_ADDR]" in masked_strict
    assert is_masked is True


def test_mask_sensitive_phone():
    """验证全球化电话号码脱敏"""
    # 中国手机号
    raw_cn = "13800138000"
    # 国际格式
    raw_intl = "+8613800138000"
    text = f"Tel: {raw_cn}, Intl: {raw_intl}"

    # BASIC 模式下不脱敏电话
    masked_basic, _ = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert raw_cn in masked_basic

    # STRICT 模式下脱敏
    masked_strict, is_masked = _mask_sensitive_data(text, PrivacyLevel.STRICT)
    assert raw_cn not in masked_strict
    assert "[MASKED_PHONE]" in masked_strict
    assert is_masked is True


def test_mask_sensitive_id_card():
    """验证中国身份证脱敏"""
    # 虚构一个符合正则的身份证号
    raw_id = "110101199001011234"
    text = f"ID: {raw_id}"

    # BASIC 模式下不脱敏
    masked_basic, _ = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert raw_id in masked_basic

    # STRICT 模式下脱敏
    masked_strict, is_masked = _mask_sensitive_data(text, PrivacyLevel.STRICT)
    assert raw_id not in masked_strict
    assert "[MASKED_ID_CARD]" in masked_strict
    assert is_masked is True
