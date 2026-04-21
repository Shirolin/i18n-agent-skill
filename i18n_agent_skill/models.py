from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConflictStrategy(str, Enum):
    """冲突解决策略"""

    OVERWRITE = "overwrite"
    KEEP_EXISTING = "keep"


class StorageFormat(str, Enum):
    """支持的存储格式"""

    JSON = "json"
    YAML = "yaml"


class PrivacyLevel(str, Enum):
    """脱敏级别"""

    STRICT = "strict"  # 屏蔽邮箱、IP、API Key、电话
    BASIC = "basic"  # 仅屏蔽 API Key 和 邮箱
    OFF = "off"  # 不脱敏


class TelemetryData(BaseModel):
    """效能观测模型"""

    duration_ms: float = Field(..., description="操作总耗时（毫秒）。")
    files_processed: int = Field(default=0, description="处理的文件数量。")
    cache_hits: int = Field(default=0, description="缓存命中次数。")
    keys_extracted: int = Field(default=0, description="提取到的词条总数。")
    tokens_saved_approx: int = Field(
        default=0, description="估算的节省 Token 数量（基于缓存和增量计算）。"
    )
    privacy_shield_hits: int = Field(default=0, description="隐私屏蔽（Masking）触发次数。")


class RegressionResult(BaseModel):
    """质量退化警告模型"""

    is_degraded: bool = Field(..., description="新翻译得分是否低于历史快照最高分。")
    snapshot_score: int = Field(..., description="快照记录的历史最高得分。")
    current_score: int = Field(..., description="本次翻译得到的评分。")
    warning_message: str = Field(..., description="建议 Agent 重新审视的原因。")


class ExtractedString(BaseModel):
    """带语义上下文的提取字符串对象"""

    text: str = Field(..., description="原文。若包含敏感信息，则会被 [MASKED_XXX] 掩码。")
    line: int = Field(..., description="在源码中的行号。")
    context: str = Field(..., description="代码上下文。")
    is_masked: bool = Field(default=False, description="是否已被脱敏。")


class ErrorInfo(BaseModel):
    """结构化错误信息"""

    error_code: str = Field(..., description="内部错误代码。")
    message: str = Field(..., description="错误描述。")
    suggested_action: str = Field(..., description="给 Agent 的下一步操作建议。")
    executable_hint: Optional[str] = Field(
        None, description="[自愈] 可直接运行以尝试修复错误的 Shell 命令。"
    )


class ValidationFeedback(BaseModel):
    """自纠错反馈模型"""

    key: str = Field(..., description="失败的 Key。")
    expected_placeholders: List[str] = Field(..., description="期望包含的占位符。")
    actual_placeholders: List[str] = Field(..., description="实际包含的占位符。")
    message: str = Field(..., description="引导建议。")


class EvaluationFeedback(BaseModel):
    """AI 自动化评审反馈模型"""

    score: int = Field(..., ge=0, le=10, description="翻译质量得分（0-10）。")
    地道度建议: str = Field(..., description="评审建议。")
    is_pass: bool = Field(..., description="是否通过。")


class StyleFeedback(BaseModel):
    """文案风格校验反馈模型"""

    key: str = Field(..., description="文案对应的 Key。")
    violation: str = Field(..., description="违规类型。")
    suggestion: str = Field(..., description="风格优化建议值。")
    message: str = Field(..., description="纠错指引。")


class ExtractInput(BaseModel):
    """提取文案的参数模型"""

    file_path: str = Field(..., description="待扫描路径。")
    use_cache: bool = Field(default=True, description="是否启用哈希缓存处理大文件。")
    vcs_mode: bool = Field(
        default=False, description="是否开启 VCS 感知模式以优化增量 Token 消耗。"
    )
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.BASIC, description="隐私脱敏级别。")


class ExtractOutput(BaseModel):
    """提取文案的输出模型"""

    results: List[ExtractedString] = Field(default_factory=list, description="提取结果。")
    is_cached: bool = Field(default=False, description="是否来自缓存。")
    glossary_context: Dict[str, str] = Field(
        default_factory=dict,
        description="[主动注入] 与本次提取文案关联的既有术语表，用于辅助 AI 翻译一致性。",
    )
    telemetry: Optional[TelemetryData] = Field(None, description="效能指标。")
    error: Optional[ErrorInfo] = Field(None, description="错误信息。")


class SyncInput(BaseModel):
    """同步 i18n 文件的参数模型"""

    new_pairs: Dict[str, str] = Field(..., description="准备写入的键值对。")
    lang_code: str = Field(..., description="目标语言。")
    base_dir: Optional[str] = Field(None, description="目标目录。")
    strategy: ConflictStrategy = Field(
        default=ConflictStrategy.KEEP_EXISTING, description="冲突策略"
    )


class SyncProposal(BaseModel):
    proposal_id: str = Field(..., description="唯一 ID")
    lang_code: str = Field(..., description="目标语言")
    changes_count: int = Field(..., description="变更条数")
    diff_summary: Dict[str, Any] = Field(..., description="变更明细")
    reasoning: str = Field(..., description="推理依据")
    file_path: str = Field(..., description="落盘路径")
    validation_errors: List[ValidationFeedback] = Field(
        default_factory=list, description="校验失败"
    )
    style_suggestions: List[StyleFeedback] = Field(default_factory=list, description="风格建议")
    regression_alert: Optional[RegressionResult] = Field(None, description="质量退化")
    telemetry: Optional[TelemetryData] = Field(None, description="效能指标")


class LearnTermInput(BaseModel):
    """进化型记忆：学习新术语。"""

    term: str = Field(..., description="原文词条。")
    translation: str = Field(..., description="确认的翻译。")
    context: Optional[str] = Field(None, description="该词条生效的上下文。")


class RefineProposalInput(BaseModel):
    """提案微调模型"""

    proposal_id: str = Field(..., description="要微调的提案 ID。")
    feedback: str = Field(..., description="人类的修改意见。")
    instruction: str = Field(..., description="给 Agent 的微调指令建议。")


class MissingKeysInput(BaseModel):
    """差异对比的参数模型"""

    lang_code: str = Field(..., description="目标对比语言。")
    base_lang: str = Field(default="en", description="基准对照语言。")
    base_dir: Optional[str] = Field(None, description="locales 目录。")


class ProjectConfig(BaseModel):
    """项目专属配置契约。"""

    source_dirs: List[str] = Field(default_factory=lambda: ["src"], description="源码目录。")
    ignore_dirs: List[str] = Field(
        default_factory=lambda: ["node_modules", "dist", "build", "tests"], description="忽略目录"
    )
    locales_dir: str = Field(default="locales", description="i18n 目录。")
    enabled_langs: List[str] = Field(
        default_factory=lambda: ["en", "zh-CN"], description="启用语言列表"
    )
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.BASIC, description="隐私级别")


class ProjectPreferences(BaseModel):
    """项目级交互偏好存储（学习型记忆）。"""

    protected_lang_key_patterns: List[str] = Field(
        default_factory=list, description="用户确认过需要开启母语保护的 Key 模式或前缀。"
    )
    ignored_keys: List[str] = Field(default_factory=list, description="用户明确要求忽略审计的 Key。")


class ProjectStatus(BaseModel):
    """预检报告模型。"""

    config: ProjectConfig = Field(..., description="配置契约。")
    has_glossary: bool = Field(..., description="是否挂载术语表。")
    cache_size: int = Field(..., description="缓存条数。")
    workspace_root: str = Field(..., description="沙箱根目录。")
    status_message: str = Field(..., description="开工建议。")
    vcs_info: Optional[Dict[str, Any]] = Field(None, description="VCS (Git) 状态信息。")
