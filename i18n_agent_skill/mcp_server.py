from mcp.server.fastmcp import FastMCP

from i18n_agent_skill.tools import (
    check_project_status,
    commit_i18n_changes,
    extract_raw_strings,
    generate_quality_report,
    get_missing_keys,
    optimize_translations,
    propose_sync_i18n,
    reference_optimize_translations,
    refine_i18n_proposal,
    sync_manual_modifications,
    update_project_glossary,
)

mcp = FastMCP("i18n-agent-skill")


@mcp.tool()
async def get_status():
    """探测当前项目的 i18n 状态，包括已启用语言、源码目录、隐私级别和 VCS (Git) 变更情况。"""
    return await check_project_status()


@mcp.tool()
async def scan_file(file_path: str, use_cache: bool = True, vcs_mode: bool = False):
    """提取指定文件中的硬编码中文。支持哈希缓存和 VCS (Git) 增量扫描。自动执行隐私脱敏。"""
    return await extract_raw_strings(file_path, use_cache, vcs_mode)


@mcp.tool()
async def audit_missing_keys(lang_code: str, base_lang: str = "en"):
    """执行差异审计：对比基准语言与目标语言，找出缺失的翻译词条。"""
    return await get_missing_keys(lang_code, base_lang)


@mcp.tool()
async def propose_sync(new_pairs: dict, lang_code: str, reasoning: str):
    """生成翻译同步提案。支持占位符校验、风格审计和质量回归预警。"""
    return await propose_sync_i18n(new_pairs, lang_code, reasoning)


@mcp.tool()
async def commit_changes(proposal_id: str):
    """正式应用并提交翻译提案，更新质量回归快照并清理临时缓存。"""
    return await commit_i18n_changes(proposal_id)


@mcp.tool()
async def refine_proposal(proposal_id: str, feedback: str):
    """根据反馈微调已生成的提案。"""
    return await refine_i18n_proposal(proposal_id, feedback)


@mcp.tool()
async def learn_term(term: str, translation: str):
    """术语持久化：将特定术语的翻译存入 GLOSSARY.json 知识库。"""
    return await update_project_glossary(term, translation)


@mcp.tool()
async def quality_audit(lang_code: str):
    """[专家巡检] 生成全量质量评审报告，识别术语冲突、不地道表达及语境错误。"""
    return await generate_quality_report(lang_code)


@mcp.tool()
async def pivot_sync(pivot_lang: str, target_lang: str, keys: list[str] | None = None):
    """[跨语言对齐] 参考熟悉语言（如 zh-CN）的翻译结果，对目标语言进行同步优化。"""
    return await reference_optimize_translations(pivot_lang, target_lang, keys)


@mcp.tool()
async def optimize_drafts(lang_code: str):
    """[幂等优化] 筛选 DRAFT 状态的词条进行批量优化，并提取已确认词条作为动态术语。"""
    return await optimize_translations(lang_code)


@mcp.tool()
async def sync_manual(lang_code: str):
    """[闭环反馈] 探测翻译文件的手动修改，并自动将其状态提升为 APPROVED。"""
    return await sync_manual_modifications(lang_code)
