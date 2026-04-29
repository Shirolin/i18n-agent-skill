import re
from dataclasses import dataclass
from typing import Any

from i18n_agent_skill.models import StyleFeedback

# ==========================================
# Text Masking Engine
# ==========================================
@dataclass
class MaskedText:
    text: str
    masks: dict[str, str]

class TextMasker:
    """
    Protects variables, URLs, and HTML tags from being destroyed by typography linters.
    """
    # Patterns to protect, ordered by priority
    PATTERNS = [
        r"https?://[^\s<>\"']+|-?[a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", # URLs
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", # Emails
        r"<[^>]+>", # HTML tags
        r"\{\{[^}]+\}\}|\{[^}]+\}", # Placeholders like {var} or {{var}}
        r"%[sdofxX]", # C-style format specifiers like %s, %d
    ]

    @classmethod
    def mask(cls, text: str) -> MaskedText:
        masks = {}
        masked_text = text
        counter = 0

        # Combine all patterns into one to avoid overlapping matches
        combined_pattern = "|".join(f"({p})" for p in cls.PATTERNS)
        
        def replace_fn(match):
            nonlocal counter
            token = f"__TOKEN_{counter}__"
            masks[token] = match.group(0)
            counter += 1
            return token

        # Only mask if there are potential matches to save time
        if re.search(combined_pattern, text):
            # Using sub with callable to handle each match uniquely
            masked_text = re.sub(combined_pattern, replace_fn, text)

        return MaskedText(text=masked_text, masks=masks)

    @classmethod
    def unmask(cls, masked_text: str, masks: dict[str, str]) -> str:
        unmasked = masked_text
        # Iterate in reverse to prevent nested token issues
        for token, original_value in reversed(masks.items()):
            unmasked = unmasked.replace(token, original_value)
        return unmasked


# ==========================================
# Language Families Definition
# ==========================================
CJK_LANGS = {"zh", "ja", "ko"}
LATIN_LANGS = {"en", "es", "fr", "de", "it", "pt", "nl", "ru", "pl", "tr", "vi", "id", "th", "hi"}

# Common language names mapping (Endonyms)
# Format: internal_id -> { "native": "Native Name", "search": [keywords for recognition] }
ENDONYM_MAP = {
    "en": {"native": "English", "search": ["english"]},
    "ja": {"native": "日本語", "search": ["japanese", "日本語"]},
    "zh": {"native": "中文", "search": ["chinese", "中文", "中国语", "中国語"]},
    "de": {"native": "Deutsch", "search": ["german", "deutsch"]},
    "ko": {"native": "한국어", "search": ["korean", "한국어"]},
    "fr": {"native": "Français", "search": ["french", "français"]},
    "es": {
        "native": "Español",
        "search": ["spanish", "español"],
    },
    "auto": {"native": "Auto", "search": ["auto"]},
}

# Semantic heuristic fingerprints: Keys matching these patterns are likely
# language selection components
LANGUAGE_SEMANTIC_PATTERNS = [r"^lang", r"^locale", r"language$", r"^pref_?lang", r"^ui_?lang"]


# ==========================================
# CJK Rules
# ==========================================
def rule_cjk_mixed_spacing(key: str, text: str) -> list[StyleFeedback]:
    """Check for missing spaces between CJK characters and Latin/digits."""
    # Covers Han characters, Hiragana, Katakana, and Hangul syllables
    cjk_pattern = r"[\u4e00-\u9fa5\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7A3]"
    new_text = text
    # CJK followed by Latin/Digit
    new_text = re.sub(f"({cjk_pattern})([a-zA-Z0-9])", r"\1 \2", new_text)
    # Latin/Digit followed by CJK
    new_text = re.sub(f"([a-zA-Z0-9])({cjk_pattern})", r"\1 \2", new_text)

    if new_text != text:
        has_cjk_en = re.search(f"{cjk_pattern}[a-zA-Z0-9]", text)
        violation_type = "MISSING_SPACE_CJK_LATIN" if has_cjk_en else "MISSING_SPACE_LATIN_CJK"
        return [
            StyleFeedback(
                key=key,
                violation=violation_type,
                suggestion=new_text,
                message=(
                    "Typography suggestion: Add space between East Asian "
                    "and Latin/digit characters for better readability."
                ),
            )
        ]
    return []


def rule_cjk_fullwidth_punctuation(key: str, text: str, exact_lang: str) -> list[StyleFeedback]:
    """Check for illegal half-width punctuation in CJK contexts."""
    # For now, only suggest full-width comma for Chinese (zh)
    if "zh" in exact_lang.lower() and "," in text and "，" not in text:
        return [
            StyleFeedback(
                key=key,
                violation="ILLEGAL_HALF_WIDTH_PUNCTUATION",
                suggestion=text.replace(",", "，"),
                message="Typography suggestion: Use full-width comma '，' in Chinese context.",
            )
        ]
    return []


def rule_protect_language_endonyms(
    key: str, text: str, lang_code: str, custom_patterns: list[str] | None = None
) -> list[StyleFeedback]:
    """
    Check for Language Endonym Protection.
    Logic: If a key has language features and the text is a known language name,
    it should remain an endonym.
    """
    k_lower = key.lower()
    t_lower = text.lower()

    # 1. Semantic detection: Does this key belong to a language switcher?
    patterns = LANGUAGE_SEMANTIC_PATTERNS + (custom_patterns or [])
    is_lang_context = any(re.search(p, k_lower) for p in patterns)

    # 2. Value detection: Is the text a known language name?
    target_native = None
    for _, info in ENDONYM_MAP.items():
        if any(kw in t_lower for kw in info["search"]):
            target_native = info["native"]
            break

    if is_lang_context and target_native:
        if text != target_native:
            return [
                StyleFeedback(
                    key=key,
                    violation="LANGUAGE_ENDONYM_OVER_TRANSLATION",
                    suggestion=target_native,
                    message=(
                        f"Semantic correction: Detected key '{key}' likely used for "
                        "language selection. Suggest using endonym "
                        f"'{target_native}' for global recognition."
                    ),
                )
            ]
    return []


# ==========================================
# Latin Rules
# ==========================================
def rule_latin_consecutive_spaces(key: str, text: str) -> list[StyleFeedback]:
    """Check for abnormal consecutive spaces in Latin contexts."""
    if "  " in text:
        new_text = re.sub(r" {2,}", " ", text)
        return [
            StyleFeedback(
                key=key,
                violation="CONSECUTIVE_SPACES",
                suggestion=new_text,
                message=(
                    "Typography suggestion: Multiple consecutive spaces detected. "
                    "Please use a single space."
                ),
            )
        ]
    return []


def rule_latin_punctuation_spacing(key: str, text: str) -> list[StyleFeedback]:
    """Check for missing space after Latin punctuation (e.g., commas, periods)."""
    # Look for punctuation (.,:?!) followed by a letter, and insert a space.
    new_text = re.sub(r"([.,:?!]+)([a-zA-Z])", r"\1 \2", text)
    if new_text != text:
        return [
            StyleFeedback(
                key=key,
                violation="MISSING_SPACE_AFTER_PUNCTUATION",
                suggestion=new_text,
                message=(
                    "Typography suggestion: A space should follow Latin punctuation "
                    "marks like commas or periods."
                ),
            )
        ]
    return []


class TranslationStyleLinter:
    """
    Multi-language typography linter.
    Uses Strategy Pattern to apply audit rules based on Language Family.
    """

    @staticmethod
    def lint(
        key: str, text: str, lang_code: str, custom_lang_patterns: list[str] | None = None
    ) -> list[StyleFeedback]:
        # 1. Apply Masking to protect variables, URLs etc.
        masked_obj = TextMasker.mask(text)
        working_text = masked_obj.text
        
        feedbacks = []
        base_lang = lang_code.split("-")[0].lower()

        # --- CJK Rule Routing ---
        if base_lang in CJK_LANGS or "zh" in base_lang:
            feedbacks.extend(rule_cjk_mixed_spacing(key, working_text))
            feedbacks.extend(rule_cjk_fullwidth_punctuation(key, working_text, lang_code))

        # --- Latin Rule Routing ---
        elif base_lang in LATIN_LANGS:
            feedbacks.extend(rule_latin_consecutive_spaces(key, working_text))
            feedbacks.extend(rule_latin_punctuation_spacing(key, working_text))

        # --- General Rules ---
        feedbacks.extend(rule_protect_language_endonyms(key, working_text, lang_code, custom_lang_patterns))

        # 2. Unmask suggestions to restore original variables
        for fb in feedbacks:
            if fb.suggestion:
                fb.suggestion = TextMasker.unmask(fb.suggestion, masked_obj.masks)

        return feedbacks
