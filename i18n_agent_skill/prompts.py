from typing import List, Optional

class PromptManager:
    """
    顶级提示词工厂：集中管理所有 Agent 指令。
    支持版本化与结构化指令生成，方便适配不同模型。
    """

    @staticmethod
    def get_translation_prompt(
        lang_code: str, 
        context: str, 
        glossary: str, 
        examples: Optional[str] = None
    ) -> str:
        return f"""你是一个精通 {lang_code} 的资深前端国际化翻译专家。

你的任务是将提供的 UI 文本翻译为 {lang_code}。

### 核心约束：
1. **术语一致性**：必须严格遵守以下术语表定义：
{glossary}

2. **代码上下文感知识别**：
当前文案所处的代码环境如下：
```typescript
{context}
```
请根据上下文判断文案的真实意图（例如：是按钮、标题还是报错提示）。

3. **格式守卫**：
- 严禁翻译或修改 `{{{{name}}}}` 或 `{{name}}` 形式的占位符。
- 严禁自行发挥，必须保持与原文语义高度契合。

### 示例 (Few-shot)：
{examples or "原文: 'Submit' -> 译文: '提交'"}

请开始翻译。"""

    @staticmethod
    def get_review_prompt(translation_json: str) -> str:
        return f"""你是一个严苛的 AI 翻译评审官。

请对以下翻译结果进行 0-10 分的质量打分：
{translation_json}

### 评审维度：
1. **准确度**：是否丢失了原文信息？
2. **地道度**：是否符合母语者的表达习惯？
3. **安全性**：占位符是否完好无损？

请按格式返回评分及改进建议。"""

    @staticmethod
    def get_refinement_prompt(proposal_id: str, feedback: str) -> str:
        return f"""用户对提案 {proposal_id} 提出了微调反馈："{feedback}"。
请基于此反馈局部更新翻译，并解释你的修正逻辑。"""
