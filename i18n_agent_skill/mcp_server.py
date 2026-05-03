from mcp.server.fastmcp import FastMCP

from i18n_agent_skill import tools

mcp = FastMCP("i18n-agent-skill")


@mcp.tool()
async def check_status():
    """
    Check the current i18n status of the project.
    Returns: Enabled languages, source directories, locales directory, and environment health.
    """
    return await tools.check_project_status()


@mcp.tool()
async def scan_strings(path: str | None = None, use_cache: bool = True, vcs_mode: bool = False):
    """
    [Extraction Phase] Extract hardcoded strings from source code.
    Args:
        path: Path to scan. If omitted, defaults to 'source_dirs' in .i18n-skill.json.
        use_cache: Whether to use hash caching for performance.
        vcs_mode: If True, only scans files modified in Git (VCS-aware).
    """
    # Note: tools.extract_raw_strings handles None path by resolution in __main__, 
    # but here we should ideally resolve it before calling tools or update tools.
    # For simplicity, we ensure tools handles defaults or __main__ logic is mirrored.
    # Implementation detail: extract_raw_strings expects a string.
    # I'll update tools.py to handle path=None safely if needed, but for now:
    target_path = path
    if not target_path:
        status = await tools.check_project_status()
        target_path = status.config.source_dirs[0] if status.config.source_dirs else "src"
        
    return await tools.extract_raw_strings(target_path, use_cache, vcs_mode)


@mcp.tool()
async def audit_missing(lang_code: str, base_lang: str = "en"):
    """
    [Validation Phase] Find keys present in base language but missing in target language.
    Args:
        lang_code: The target language to check (e.g., 'zh-CN', 'ja').
        base_lang: The reference language (defaults to 'en').
    """
    return await tools.get_missing_keys(lang_code, base_lang)


@mcp.tool()
async def cleanup_unused(lang_code: str = "en"):
    """
    [Cleanup Phase] Identify i18n keys present in locale files but never used in source code.
    Args:
        lang_code: Language file to audit for dead keys.
    """
    return await tools.get_dead_keys(lang_code)


@mcp.tool()
async def propose_sync(new_pairs: dict, lang_code: str, reason: str = "Manual sync"):
    """
    [Sync Phase] Generate a translation synchronization proposal.
    Args:
        new_pairs: A flat dictionary of { "key": "translation" } to be merged.
        lang_code: Target language code.
        reason: Justification for the change (e.g., 'Fixing typo', 'New feature extraction').
    Returns: A SyncProposal including a link to a Markdown Preview file.
    """
    return await tools.propose_sync_i18n(new_pairs, lang_code, reason)


@mcp.tool()
async def commit_changes(target_scope: str):
    """
    [Commit Phase] Formally apply pending proposals to the physical locale files.
    Args:
        target_scope: Either a specific language code (e.g., 'zh-CN') or the literal string 'all'.
    """
    return await tools.commit_i18n_changes(target_scope)


@mcp.tool()
async def refine_proposal(proposal_id: str, feedback: str):
    """
    Refine an existing proposal based on human feedback.
    Args:
        proposal_id: Language code or proposal identifier.
        feedback: Description of what to adjust.
    """
    return await tools.refine_i18n_proposal(proposal_id, feedback)


@mcp.tool()
async def save_glossary(term: str, translation: str):
    """
    Save a confirmed term translation into GLOSSARY.json to ensure future consistency.
    """
    return await tools.update_project_glossary(term, translation)


@mcp.tool()
async def audit_quality(lang_code: str):
    """
    [Expert Audit] Generate a full quality report with typography and variable safety checks.
    Args:
        lang_code: Language to review.
    """
    return await tools.generate_quality_report(lang_code)


@mcp.tool()
async def pivot_sync(pivot_lang: str, target_lang: str):
    """
    [Semantic Alignment] Use a familiar language as a reference to optimize a target language.
    Args:
        pivot_lang: Reference language (e.g., 'zh-CN').
        target_lang: Language to be improved (e.g., 'ja').
    """
    return await tools.reference_optimize_translations(pivot_lang, target_lang)


@mcp.tool()
async def optimize_targets(lang_code: str, include_approved: bool = False):
    """
    [Optimization Phase] Export unpolished or non-approved entries for batch AI optimization.
    Args:
        lang_code: Target language.
        include_approved: If True, even approved entries will be exported for re-polishing.
    """
    return await tools.optimize_translations(lang_code, include_approved)


@mcp.tool()
async def learn_fixes(lang_code: str):
    """
    [Learning Loop] Detect manual modifications in locale files and promote them to APPROVED status.
    Args:
        lang_code: Language file to learn from.
    """
    return await tools.sync_manual_modifications(lang_code)


@mcp.tool()
async def distill_persona():
    """
    Extract project metadata to help the AI understand the business domain and tone.
    """
    return await tools.distill_project_persona()


@mcp.tool()
async def save_persona(persona_data: dict):
    """
    Save confirmed business persona (domain, audience, tone) to configuration.
    Args:
        persona_data: Dictionary containing 'domain', 'audience', and 'tone'.
    """
    return await tools.save_project_persona(persona_data)
