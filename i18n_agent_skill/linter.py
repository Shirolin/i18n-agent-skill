import re
from typing import List

from i18n_agent_skill.models import StyleFeedback

# ==========================================
# Language Families Definition
# ==========================================
CJK_LANGS = {"zh", "ja", "ko"}
LATIN_LANGS = {
    "en", "es", "fr", "de", "it", "pt", "nl", "ru", 
    "pl", "tr", "vi", "id", "th", "hi"
}

# TODO: 未来引入 StrictnessLevel 配置（如 Basic, Strict, Off）
# 并在 Rule 函数调用时注入 Config 以调整校验严格度。

# ==========================================
# CJK Rules
# ==========================================
def rule_cjk_mixed_spacing(key: str, text: str) -> List[StyleFeedback]:
    """检查 CJK（中日韩）语系文本与西文数字混排时的空格建议"""
    # 覆盖汉字、日文假名、韩文音节
    cjk_pattern = r'[\u4e00-\u9fa5\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7A3]'
    new_text = text
    # CJK 紧跟英文/数字
    new_text = re.sub(f'({cjk_pattern})([a-zA-Z0-9])', r'\1 \2', new_text)
    # 英文/数字紧跟 CJK
    new_text = re.sub(f'([a-zA-Z0-9])({cjk_pattern})', r'\1 \2', new_text)
    
    if new_text != text:
        has_cjk_en = re.search(f'{cjk_pattern}[a-zA-Z0-9]', text)
        violation_type = "MISSING_SPACE_CJK_LATIN" if has_cjk_en else "MISSING_SPACE_LATIN_CJK"
        return [StyleFeedback(
            key=key,
            violation=violation_type,
            suggestion=new_text,
            message="排版建议：在东亚字符与西文/数字之间添加空格以优化阅读体验。"
        )]
    return []

def rule_cjk_fullwidth_punctuation(key: str, text: str, exact_lang: str) -> List[StyleFeedback]:
    """检查非法半角标点（主要用于中文环境）"""
    # 避免日文「、」「。」的复杂替换逻辑干扰，暂时仅建议对 zh 开启逗号校验
    if "zh" in exact_lang.lower() and "," in text and "，" not in text:
        return [StyleFeedback(
            key=key,
            violation="ILLEGAL_HALF_WIDTH_PUNCTUATION",
            suggestion=text.replace(",", "，"),
            message="排版建议：中文语境下建议使用全角逗号 '，'。"
        )]
    return []


# ==========================================
# Latin Rules
# ==========================================
def rule_latin_consecutive_spaces(key: str, text: str) -> List[StyleFeedback]:
    """检查西文语境下的异常连续空格"""
    if "  " in text:
        # 将 2个及以上连续空格 替换为 1个
        new_text = re.sub(r' {2,}', ' ', text)
        return [StyleFeedback(
            key=key,
            violation="CONSECUTIVE_SPACES",
            suggestion=new_text,
            message="排版建议：检测到多余的连续空格，请保留单一空格。"
        )]
    return []

def rule_latin_punctuation_spacing(key: str, text: str) -> List[StyleFeedback]:
    """检查西文标点（如逗号、句号等）之后是否缺少空格"""
    # 逻辑：查找标点符号（.,:?!），若后面紧跟着字母，则插入空格。
    # 这样自动排除了小数点和千分位（因为它们后面跟着的是数字，不会被 [a-zA-Z] 命中）。
    new_text = re.sub(r'([.,:?!]+)([a-zA-Z])', r'\1 \2', text)
    if new_text != text:
        return [StyleFeedback(
            key=key,
            violation="MISSING_SPACE_AFTER_PUNCTUATION",
            suggestion=new_text,
            message="排版建议：西文标点符号（如逗号、句号）之后应跟随一个空格。"
        )]
    return []


class TranslationStyleLinter:
    """
    多语言文案排版规范校验器。
    采用策略模式，基于 Language Family 执行不同的审计规则。
    当前所有反馈级别均为 Suggestion。
    """
    
    @staticmethod
    def lint(key: str, text: str, lang_code: str) -> List[StyleFeedback]:
        feedbacks = []
        base_lang = lang_code.split("-")[0].lower()
        
        # --- CJK 规则路由 ---
        if base_lang in CJK_LANGS or "zh" in base_lang:  # 容错处理中文繁体
            feedbacks.extend(rule_cjk_mixed_spacing(key, text))
            feedbacks.extend(rule_cjk_fullwidth_punctuation(key, text, lang_code))
            
        # --- Latin 规则路由 ---
        elif base_lang in LATIN_LANGS:
            feedbacks.extend(rule_latin_consecutive_spaces(key, text))
            feedbacks.extend(rule_latin_punctuation_spacing(key, text))
            
        return feedbacks

