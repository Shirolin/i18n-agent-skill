from enum import Enum
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field

class ConflictStrategy(str, Enum):
    """冲突解决策略：定义当翻译后的 Key 在目标文件中已存在且值不同时的行为。"""
    OVERWRITE = "overwrite"       # 覆盖已有翻译：Agent 认为其生成的翻译质量更高或更符合当前需求。
    KEEP_EXISTING = "keep"        # 保留已有翻译：优先保护人类开发者的既有工作，Agent 仅做增量补充。

class StorageFormat(str, Enum):
    """支持的存储格式：本项目目前优先支持标准 JSON 格式。"""
    JSON = "json"
    YAML = "yaml"

class ExtractedString(BaseModel):
    """带语义上下文的提取字符串对象：用于辅助 Agent 精准判断文案意图。"""
    text: str = Field(..., description="提取到的文案原文。请分析其语义。")
    line: int = Field(..., description="文案在源代码中的行号。")
    context: str = Field(..., description="该文案周围的代码上下文（前后各 1-2 行）。请利用此上下文判断文案是按钮、标题还是错误提示。")

class ErrorInfo(BaseModel):
    """Agent 友好的结构化错误信息：用于引导 Agent 自主纠错。"""
    error_code: str = Field(..., description="内部错误代码，Agent 应根据代码采取不同策略。")
    message: str = Field(..., description="详细错误描述。")
    suggested_action: str = Field(..., description="【关键指引】给 Agent 的下一步纠错建议。请务必优先执行此动作。")

class ValidationFeedback(BaseModel):
    """自纠错反馈模型：指示校验失败的具体细节，用于 Agent '补考' 重试。"""
    key: str = Field(..., description="校验失败的 JSON 路径（Key）。")
    expected_placeholders: List[str] = Field(..., description="原文中存在的、翻译后也必须保留的占位符列表。")
    actual_placeholders: List[str] = Field(..., description="你当前生成的翻译中实际包含的占位符。")
    message: str = Field(..., description="【纠错引导】告诉你具体的错误原因。请根据此反馈重新翻译该词条。")

class ExtractInput(BaseModel):
    """提取文案的参数模型：引导 Agent 安全、高效地扫描源码。"""
    file_path: str = Field(..., description="待扫描源码文件的路径。禁止扫描 node_modules 或 build 目录。建议先调用 check_project_status 获取项目结构。")
    use_cache: bool = Field(default=True, description="是否启用哈希缓存。在大规模项目中，启用缓存可极大提高效率并节省 Token。")

class ExtractOutput(BaseModel):
    """提取文案的输出模型。"""
    results: List[ExtractedString] = Field(default_factory=list, description="提取到的字符串列表及上下文。")
    is_cached: bool = Field(default=False, description="结果是否来自缓存。")
    error: Optional[ErrorInfo] = Field(None, description="如果发生错误，Agent 应根据 error.suggested_action 决定是否重试或报告。")

class SyncInput(BaseModel):
    """同步 i18n 文件的参数模型。"""
    new_pairs: Dict[str, str] = Field(..., description="准备写入的键值对。Key 必须采用点号分隔的嵌套路径风格。")
    lang_code: str = Field(..., description="目标语言代码（如 'zh-CN'）。请确保该代码在项目已启用语言列表中。")
    base_dir: Optional[str] = Field(None, description="目标目录。如果不填，系统将基于 .i18n-skill.json 或自动探测。")
    strategy: ConflictStrategy = Field(default=ConflictStrategy.KEEP_EXISTING, description="冲突策略。除非用户明确要求强制刷新，否则建议使用 'keep'。")

class SyncProposal(BaseModel):
    """双阶段提交：变更提案。在真实执行写入前，Agent 必须以此模型向用户申请授权。"""
    proposal_id: str = Field(..., description="唯一的提案标识符。")
    lang_code: str = Field(..., description="语言代码。")
    changes_count: int = Field(..., description="即将修改或新增的词条总数。")
    diff_summary: Dict[str, Any] = Field(..., description="即将发生的变更明细摘要。")
    reasoning: str = Field(..., description="【追溯依据】解释你为什么要进行这些修改。如果是基于上下文或术语表，请在此说明。")
    file_path: str = Field(..., description="最终落盘的物理路径。")
    validation_errors: List[ValidationFeedback] = Field(default_factory=list, description="【自省反馈】如果此列表不为空，禁止向用户提议，你必须先解决这些占位符错误。")

class MissingKeysInput(BaseModel):
    """差异对比的参数模型。"""
    lang_code: str = Field(..., description="目标对比语言。")
    base_lang: str = Field(default="en", description="基准对照语言。")
    base_dir: Optional[str] = Field(None, description="locales 目录。")

class ProjectConfig(BaseModel):
    """项目专属配置契约：由 .i18n-skill.json 定义。"""
    source_dirs: List[str] = Field(default_factory=lambda: ["src"], description="项目源码目录。")
    ignore_dirs: List[str] = Field(default_factory=lambda: ["node_modules", "dist", "build", "tests"], description="扫描时应忽略的目录。")
    locales_dir: str = Field(default="locales", description="i18n 语言文件存放根目录。")
    enabled_langs: List[str] = Field(default_factory=lambda: ["en", "zh-CN"], description="项目已启用的语言列表。")

class ProjectStatus(BaseModel):
    """预检报告模型：帮助 Agent 在开工前快速“熟悉环境”。"""
    config: ProjectConfig = Field(..., description="当前项目生效的配置契约。")
    has_glossary: bool = Field(..., description="项目是否已挂载术语表。")
    cache_size: int = Field(..., description="当前本地哈希缓存的文件条数。")
    workspace_root: str = Field(..., description="当前安全沙箱锁定的根目录。")
    status_message: str = Field(..., description="给 Agent 的开工建议信息。")
