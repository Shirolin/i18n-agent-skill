import re
from typing import List
from i18n_agent_skill.models import StyleFeedback

class TranslationStyleLinter:
    """
    大师级文案风格校验器。
    核心规则：
    1. 中英混排空格校验（盘古之白）。
    2. 标点符号中文化校验。
    """
    
    @staticmethod
    def lint(key: str, text: str, lang_code: str) -> List[StyleFeedback]:
        feedbacks = []
        
        # 仅针对中文语境执行风格校验
        if "zh" in lang_code.lower():
            # 规则 1：中英混排缺失空格
            # 中文紧跟英文
            if re.search(r'[\u4e00-\u9fa5][a-zA-Z0-9]', text):
                feedbacks.append(StyleFeedback(
                    key=key,
                    violation="MISSING_SPACE_ZH_EN",
                    suggestion=re.sub(r'([\u4e00-\u9fa5])([a-zA-Z0-9])', r'\1 \2', text),
                    message="中英文混排建议在中文与英文/数字之间添加空格。"
                ))
            # 英文紧跟中文
            elif re.search(r'[a-zA-Z0-9][\u4e00-\u9fa5]', text):
                feedbacks.append(StyleFeedback(
                    key=key,
                    violation="MISSING_SPACE_EN_ZH",
                    suggestion=re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fa5])', r'\1 \2', text),
                    message="中英文混排建议在英文/数字与中文之间添加空格。"
                ))
                
            # 规则 2：非法半角标点
            if "," in text and "，" not in text:
                feedbacks.append(StyleFeedback(
                    key=key,
                    violation="ILLEGAL_HALF_WIDTH_PUNCTUATION",
                    suggestion=text.replace(",", "，"),
                    message="中文语境下建议使用全角逗号 '，' 而非半角逗号 ','。"
                ))
                
        return feedbacks
