from i18n_agent_skill.models import PrivacyLevel
from i18n_agent_skill.tools import _mask_sensitive_data


def test_mask_sensitive_email():
    """验证邮箱脱敏"""
    text = "联系我: test@example.com"
    masked, is_masked = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert "test@example.com" not in masked
    assert "[MASKED_EMAIL]" in masked
    assert is_masked is True

def test_mask_sensitive_api_key():
    """验证 API Key 脱敏"""
    fake_key = f"sk-{'b'*24}"
    text = f"apiKey = '{fake_key}'"
    masked, is_masked = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert fake_key not in masked
    assert "[MASKED_API_KEY]" in masked
    assert is_masked is True

def test_privacy_level_off():
    """验证关闭脱敏时的行为"""
    text = "key: sk-12345, mail: a@b.com"
    masked, is_masked = _mask_sensitive_data(text, PrivacyLevel.OFF)
    assert masked == text
    assert is_masked is False

def test_privacy_level_strict_ip():
    """验证 STRICT 级别下对 IP 的脱敏"""
    text = "Server IP: 192.168.1.1"
    # BASIC 模式下不脱敏 IP
    masked_basic, _ = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert "192.168.1.1" in masked_basic
    
    # STRICT 模式下脱敏 IP
    masked_strict, is_masked = _mask_sensitive_data(text, PrivacyLevel.STRICT)
    assert "192.168.1.1" not in masked_strict
    assert "[MASKED_IP_ADDR]" in masked_strict
    assert is_masked is True
