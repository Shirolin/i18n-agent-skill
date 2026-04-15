import os

from mcp.server.fastmcp import FastMCP

from i18n_agent_skill.tools import (
    WORKSPACE_ROOT,
    check_project_status,
    commit_i18n_changes,
    extract_raw_strings,
    get_missing_keys,
    load_project_glossary,
    propose_sync_i18n,
    refine_i18n_proposal,
    update_project_glossary,
)

# 创建 MCP Server 实例
mcp = FastMCP("i18n-agent-skill")

# =========================================================
# MCP Resources: 让 AI 具备“实时全局视野”
# =========================================================

@mcp.resource("i18n://glossary")
async def get_glossary_resource() -> str:
    """获取当前项目的术语表原文。"""
    glossary = await load_project_glossary()
    import json
    return json.dumps(glossary, indent=2, ensure_ascii=False)

@mcp.resource("i18n://locales/{lang}")
async def get_locale_resource(lang: str) -> str:
    """获取指定语言的翻译字典资源。"""
    from i18n_agent_skill.tools import _detect_locale_dir
    target_dir = _detect_locale_dir()
    file_path = os.path.join(WORKSPACE_ROOT, target_dir, f"{lang}.json")
    if not os.path.exists(file_path):
        return "{}"
    import aiofiles
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        return await f.read()

# =========================================================
# MCP Tools: 暴露核心原子工具
# =========================================================

@mcp.tool()
async def get_status():
    """大师级预检：获取当前项目结构、Git 变动状态及配置契约。"""
    return await check_project_status()

@mcp.tool()
async def scan_file(file_path: str, use_cache: bool = True, vcs_mode: bool = False):
    """语义提取：从源文件中提取 UI 文案及其代码上下文。支持 Git 增量感知。"""
    return await extract_raw_strings(file_path, use_cache, vcs_mode)

@mcp.tool()
async def find_missing(lang_code: str, base_lang: str = "en"):
    """对比差异：找出目标语言中缺失的翻译条目。"""
    return await get_missing_keys(lang_code, base_lang)

@mcp.tool()
async def propose_sync(new_pairs: dict, lang_code: str, reasoning: str, strategy: str = "keep"):
    """变更提议：生成翻译提案。包含占位符校验、文案风格 Linter 与 AI 评审插槽。"""
    from i18n_agent_skill.models import ConflictStrategy
    strat = (
        ConflictStrategy.OVERWRITE if strategy == "overwrite" 
        else ConflictStrategy.KEEP_EXISTING
    )
    return await propose_sync_i18n(new_pairs, lang_code, reasoning, strategy=strat)

@mcp.tool()
async def commit_changes(proposal_id: str):
    """安全提交：在人工确认提案后，执行物理文件落盘。"""
    return await commit_i18n_changes(proposal_id)

@mcp.tool()
async def refine_proposal(proposal_id: str, feedback: str):
    """交互微调：根据人类的反馈意见修改已生成的提案。"""
    return await refine_i18n_proposal(proposal_id, feedback)

@mcp.tool()
async def learn_term(term: str, translation: str):
    """进化记忆：将特定术语的翻译持久化到 GLOSSARY.json 知识库中。"""
    return await update_project_glossary(term, translation)

if __name__ == "__main__":
    mcp.run()
