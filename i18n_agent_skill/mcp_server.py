from mcp.server.fastmcp import FastMCP

from i18n_agent_skill import tools

mcp = FastMCP("i18n-agent-skill")


@mcp.tool()
async def check_status():
    """
    Check the current i18n status of the project, including enabled languages,
    source directories, privacy levels, and VCS (Git) changes.
    """
    return await tools.check_project_status()


@mcp.tool()
async def scan_strings(path: str, use_cache: bool = True, vcs_mode: bool = False):
    """
    Extract hardcoded strings from specified files or directories.
    Supports hash caching and VCS (Git) incremental scanning.
    Automatically performs privacy masking.
    """
    return await tools.extract_raw_strings(path, use_cache, vcs_mode)


@mcp.tool()
async def audit_missing(lang_code: str, base_lang: str = "en"):
    """
    Perform differential audit: compare the base language with the target language
    to find missing translation keys.
    """
    return await tools.get_missing_keys(lang_code, base_lang)


@mcp.tool()
async def propose_sync(new_pairs: dict, lang_code: str, reason: str = "Manual sync"):
    """
    Generate a translation synchronization proposal.
    For large data (>5 items), passing the absolute path to a JSON file is recommended
    to prevent truncation.
    """
    return await tools.propose_sync_i18n(new_pairs, lang_code, reason)


@mcp.tool()
async def commit_changes(proposal_id: str):
    """
    Formally apply and commit a translation proposal,
    update quality regression snapshots, and clean up temporary caches.
    """
    return await tools.commit_i18n_changes(proposal_id)


@mcp.tool()
async def refine_proposal(proposal_id: str, feedback: str):
    """
    Refine an existing proposal based on human feedback.
    """
    return await tools.refine_i18n_proposal(proposal_id, feedback)


@mcp.tool()
async def save_glossary(term: str, translation: str):
    """
    Terminology persistence: Save specific term translations into the GLOSSARY.json knowledge base.
    """
    return await tools.update_project_glossary(term, translation)


@mcp.tool()
async def audit_quality(lang_code: str):
    """
    [Expert Audit] Generate a full quality review report.
    Results are exported to a Markdown audit report file.
    """
    return await tools.generate_quality_report(lang_code)


@mcp.tool()
async def pivot_sync(pivot_lang: str, target_lang: str):
    """
    [Cross-Language Alignment] Optimize the target language by referencing
    translation results from a familiar language (e.g., zh-CN).
    """
    return await tools.reference_optimize_translations(pivot_lang, target_lang)


@mcp.tool()
async def optimize_targets(lang_code: str, include_approved: bool = False):
    """
    [Batch Optimization] Identify entries to be optimized and export them as a task file.
    Set include_approved=True for full polishing of existing entries.
    """
    return await tools.optimize_translations(lang_code, include_approved)


@mcp.tool()
async def learn_fixes(lang_code: str):
    """
    [Feedback Loop] Detect manual modifications in translation files
    and automatically promote their status to APPROVED.
    """
    return await tools.sync_manual_modifications(lang_code)


@mcp.tool()
async def distill_persona():
    """
    [Agentic Distillation] Sample project metadata to help AI infer the business persona.
    """
    return await tools.distill_project_persona()


@mcp.tool()
async def save_persona(persona_data: dict):
    """
    Save the confirmed business persona (domain, audience, tone) to configuration.
    """
    return await tools.save_project_persona(persona_data)
