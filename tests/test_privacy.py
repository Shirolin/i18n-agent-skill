from i18n_agent_skill.models import PrivacyLevel
from i18n_agent_skill.tools import _mask_sensitive_data


def test_email_masking():
    """Verify email address masking."""
    # Dynamically concatenate to avoid direct matches by scanners
    email_addr = "user" + "@" + "example.com"
    text = f"Contact me at: {email_addr}"

    masked, is_m = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert is_m is True
    assert email_addr not in masked
    assert "[MASKED_EMAIL]" in masked


def test_api_key_masking():
    """Verify OpenAI-style API Key masking."""
    api_key = "sk-" + "a" * 20
    text = f"My key is {api_key}"

    masked, is_m = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert is_m is True
    assert api_key not in masked
    assert "[MASKED_API_KEY]" in masked


def test_masking_off():
    """Verify behavior when privacy masking is turned off."""
    text = "Secret: sk-12345678901234567890"
    masked, is_m = _mask_sensitive_data(text, PrivacyLevel.OFF)
    assert is_m is False
    assert masked == text


def test_strict_mode_ip():
    """Verify IP address masking under STRICT level."""
    ip = "192.168.1.1"
    text = f"Internal IP: {ip}"

    # No masking in BASIC mode for IP
    masked_basic, is_m_basic = _mask_sensitive_data(text, PrivacyLevel.BASIC)
    assert is_m_basic is False

    # Masking in STRICT mode for IP
    masked_strict, is_m_strict = _mask_sensitive_data(text, PrivacyLevel.STRICT)
    assert is_m_strict is True
    assert ip not in masked_strict
    assert "[MASKED_IP_ADDR]" in masked_strict


def test_phone_masking():
    """Verify globalized phone number masking."""
    # Chinese mobile
    cn_mobile = "13812345678"
    # International format
    intl_phone = "+8613812345678"

    # No masking in BASIC mode for phone
    _, is_m_basic = _mask_sensitive_data(cn_mobile, PrivacyLevel.BASIC)
    assert is_m_basic is False

    # Masking in STRICT mode
    masked, is_m_strict = _mask_sensitive_data(intl_phone, PrivacyLevel.STRICT)
    assert is_m_strict is True
    assert "[MASKED_PHONE]" in masked


def test_id_card_masking():
    """Verify ID card number masking."""
    # Fictional ID number
    id_num = "11010119900101123X"

    # No masking in BASIC mode
    _, is_m_basic = _mask_sensitive_data(id_num, PrivacyLevel.BASIC)
    assert is_m_basic is False

    # Masking in STRICT mode
    masked, is_m_strict = _mask_sensitive_data(id_num, PrivacyLevel.STRICT)
    assert is_m_strict is True
    assert "[MASKED_ID_CARD]" in masked
