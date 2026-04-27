from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConflictStrategy(str, Enum):
    """Conflict resolution strategy"""

    OVERWRITE = "overwrite"
    KEEP_EXISTING = "keep"


class TranslationStatus(str, Enum):
    """Translation lifecycle status"""

    DRAFT = "draft"  # AI generated, rewritable
    REVIEWED = "reviewed"  # Manually reviewed, edit with care
    APPROVED = "approved"  # Confirmed/Featured, absolute protection (idempotency cornerstone)


class StorageFormat(str, Enum):
    """Supported storage formats"""

    JSON = "json"
    YAML = "yaml"


class PrivacyLevel(str, Enum):
    """Privacy masking level"""

    STRICT = "strict"  # Mask email, IP, API Key, phone
    BASIC = "basic"  # Mask API Key and email only
    OFF = "off"  # No masking


class TelemetryData(BaseModel):
    """Performance telemetry model"""

    duration_ms: float = Field(..., description="Total operation duration in milliseconds.")
    files_processed: int = Field(default=0, description="Number of files processed.")
    cache_hits: int = Field(default=0, description="Number of cache hits.")
    keys_extracted: int = Field(default=0, description="Total number of keys extracted.")
    tokens_saved_approx: int = Field(
        default=0, description="Estimated tokens saved based on cache and incremental computation."
    )
    privacy_shield_hits: int = Field(default=0, description="Number of privacy masking hits.")


class RegressionResult(BaseModel):
    """Quality regression warning model"""

    is_degraded: bool = Field(
        ..., description="Whether the new translation score is lower than history."
    )
    snapshot_score: int = Field(..., description="Highest historical score in snapshots.")
    current_score: int = Field(..., description="Score for the current translation.")
    warning_message: str = Field(..., description="Reason for the Agent to re-examine.")


class ExtractedString(BaseModel):
    """Extracted string object with semantic context"""

    text: str = Field(..., description="Source text. Masked with [MASKED_XXX] if sensitive.")
    line: int = Field(..., description="Line number in source file.")
    context: str = Field(..., description="Code context.")
    is_masked: bool = Field(default=False, description="Whether the text is masked.")


class ErrorInfo(BaseModel):
    """Structured error information"""

    error_code: str = Field(..., description="Internal error code.")
    message: str = Field(..., description="Error description.")
    suggested_action: str = Field(..., description="Next step suggestion for the Agent.")
    executable_hint: str | None = Field(
        None, description="[Self-healing] Shell command to try and fix the error."
    )


class ValidationFeedback(BaseModel):
    """Self-correction feedback model"""

    key: str = Field(..., description="The failing key.")
    expected_placeholders: list[str] = Field(
        ..., description="Placeholders expected to be present."
    )
    actual_placeholders: list[str] = Field(..., description="Placeholders actually found.")
    message: str = Field(..., description="Guidance for correction.")


class EvaluationFeedback(BaseModel):
    """AI automated review feedback model"""

    score: int = Field(..., ge=0, le=10, description="Translation quality score (0-10).")
    fluency_suggestions: str = Field(..., description="Review suggestions.")
    is_pass: bool = Field(..., description="Whether the quality check passed.")


class StyleFeedback(BaseModel):
    """Typography style validation feedback model"""

    key: str = Field(..., description="Key corresponding to the text.")
    violation: str = Field(..., description="Violation type.")
    suggestion: str = Field(..., description="Suggested value for style optimization.")
    message: str = Field(..., description="Correction guidance.")


class ReviewItem(BaseModel):
    """Controversial/Pending review item"""

    key: str = Field(..., description="Key of the review item.")
    current_translation: str = Field(..., description="Current translation content.")
    suggested_translation: str = Field(..., description="AI suggested translation.")
    issue_type: str = Field(
        ..., description="Issue type (e.g., Inconsistency, Context, Not Native)."
    )
    confidence: str = Field(..., description="AI confidence in the suggestion (High/Medium/Low).")
    reasoning: str = Field(..., description="Reason for improvement.")


class EvaluationReport(BaseModel):
    """Full quality review report"""

    lang_code: str = Field(..., description="Language being reviewed.")
    total_keys: int = Field(..., description="Total number of keys.")
    approved_keys: int = Field(..., description="Number of approved (skip review) keys.")
    controversial_items: list[ReviewItem] = Field(
        default_factory=list, description="List of controversial/target keys."
    )
    overall_score: int = Field(..., description="Overall health score (0-100).")
    summary: str = Field(..., description="Expert summary and next steps.")
    report_file_path: str | None = Field(
        None, description="Path to the generated Markdown audit report file."
    )


class PivotSyncInput(BaseModel):
    """Cross-language reference sync parameters"""

    pivot_lang: str = Field(..., description="Reference mapping language (e.g., zh-CN).")
    target_lang: str = Field(..., description="Target language to be synced (e.g., ja).")
    keys_to_sync: list[str] | None = Field(
        None, description="List of keys to reference. Full scan if null."
    )


class ExtractInput(BaseModel):
    """Parameters for string extraction"""

    file_path: str = Field(..., description="Path to scan.")
    use_cache: bool = Field(default=True, description="Whether to use hash cache.")
    vcs_mode: bool = Field(
        default=False, description="Enable VCS-aware mode for incremental scanning."
    )
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.BASIC, description="Privacy level.")


class ExtractOutput(BaseModel):
    """Output model for string extraction"""

    results: list[ExtractedString] = Field(default_factory=list, description="Extraction results.")
    is_cached: bool = Field(default=False, description="Whether from cache.")
    glossary_context: dict[str, str] = Field(
        default_factory=dict,
        description="[Proactive Injection] Relevant glossary to aid AI consistency.",
    )
    telemetry: TelemetryData | None = Field(None, description="Performance metrics.")
    error: ErrorInfo | None = Field(None, description="Error information.")


class SyncInput(BaseModel):
    """Parameters for i18n file sync"""

    new_pairs: dict[str, str] = Field(..., description="Key-value pairs to write.")
    lang_code: str = Field(..., description="Target language.")
    base_dir: str | None = Field(None, description="Target directory.")
    strategy: ConflictStrategy = Field(
        default=ConflictStrategy.KEEP_EXISTING, description="Conflict strategy."
    )


class SyncProposal(BaseModel):
    """Synchronization proposal model"""

    proposal_id: str = Field(..., description="Unique ID.")
    lang_code: str = Field(..., description="Target language.")
    changes_count: int = Field(..., description="Number of changes.")
    diff_summary: dict[str, Any] = Field(..., description="Diff details.")
    reasoning: str = Field(..., description="Reasoning.")
    file_path: str = Field(..., description="File path.")
    validation_errors: list[ValidationFeedback] = Field(
        default_factory=list, description="Validation errors."
    )
    style_suggestions: list[StyleFeedback] = Field(
        default_factory=list, description="Style suggestions."
    )
    preview_file_path: str | None = Field(None, description="Generated Markdown preview file path.")
    regression_alert: RegressionResult | None = Field(None, description="Quality regression.")
    telemetry: TelemetryData | None = Field(None, description="Performance metrics.")


class LearnTermInput(BaseModel):
    """Evolutionary memory: Learning a new term."""

    term: str = Field(..., description="Source term.")
    translation: str = Field(..., description="Confirmed translation.")
    context: str | None = Field(None, description="Context of the term.")


class RefineProposalInput(BaseModel):
    """Proposal refinement model"""

    proposal_id: str = Field(..., description="Proposal ID to refine.")
    feedback: str = Field(..., description="Human feedback.")
    instruction: str = Field(..., description="Suggested instruction for the Agent.")


class MissingKeysInput(BaseModel):
    """Parameters for differential audit"""

    lang_code: str = Field(..., description="Target comparison language.")
    base_lang: str = Field(default="en", description="Base reference language.")
    base_dir: str | None = Field(None, description="Locales directory.")


class ProjectPersona(BaseModel):
    """Project business persona model"""

    domain: str = Field(
        default="", description="Business domain (e.g., Fintech, E-commerce, Gaming)"
    )
    audience: str = Field(
        default="", description="Target audience (e.g., B2B Professionals, Gen Z Users)"
    )
    tone: str = Field(default="", description="Expected tone (e.g., Formal, Friendly, Humorous)")
    custom_guidelines: list[str] = Field(
        default_factory=list, description="Other custom translation guidelines"
    )


class ProjectConfig(BaseModel):
    """Project configuration contract."""

    source_dirs: list[str] = Field(
        default_factory=lambda: ["src"], description="Source directories."
    )
    ignore_dirs: list[str] = Field(
        default_factory=lambda: ["node_modules", "dist", "build", "tests"],
        description="Ignore directories.",
    )
    locales_dir: str = Field(default="locales", description="i18n directory.")
    enabled_langs: list[str] = Field(
        default_factory=lambda: ["en", "zh-CN"], description="Enabled languages."
    )
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.BASIC, description="Privacy level.")

    # Persona for idiomatic translations
    persona: ProjectPersona = Field(default_factory=ProjectPersona, description="Business persona.")

    # Evolutionary memory fields
    protected_lang_key_patterns: list[str] = Field(
        default_factory=list, description="Patterns for endonym protection."
    )
    ignored_keys: list[str] = Field(default_factory=list, description="Keys ignored in audit.")


class ProjectStatus(BaseModel):
    """Pre-check report model."""

    config: ProjectConfig = Field(..., description="Project config.")
    has_glossary: bool = Field(..., description="Glossary mounted.")
    cache_size: int = Field(..., description="Cache count.")
    workspace_root: str = Field(..., description="Workspace root.")
    status_message: str = Field(..., description="Deployment suggestion.")
    vcs_info: dict[str, Any] | None = Field(None, description="VCS (Git) status.")
