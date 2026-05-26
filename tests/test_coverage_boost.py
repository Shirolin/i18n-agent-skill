import json
import os
import shutil
import tempfile

import aiofiles
import pytest

from i18n_agent_skill import tools
from i18n_agent_skill.tools import (
    _load_locale_data,
    _save_locale_data,
    _validate_safe_path,
    check_project_status,
    extract_raw_strings,
    initialize_project_config,
    load_project_glossary,
    propose_sync_i18n,
    save_project_persona,
    set_workspace_root,
    update_project_glossary,
)


@pytest.fixture
def temp_workspace():
    test_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(test_dir, "locales"))
    set_workspace_root(test_dir)
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_ts_locale_support(temp_workspace):
    """Test loading and saving .ts locale files (JS object literal parsing)."""
    locales_dir = os.path.join(temp_workspace, "locales")
    ts_file = os.path.join(locales_dir, "en.ts")

    # 1. Test Save as .ts
    data = {"auth": {"login": "Login Now"}}
    await _save_locale_data(ts_file, data)

    with open(ts_file, encoding="utf-8") as f:
        content = f.read()
        assert "export default {" in content
        assert '"login": "Login Now"' in content

    # 2. Test Load from .ts
    loaded = await _load_locale_data(locales_dir, "en")
    assert loaded["auth"]["login"] == "Login Now"


@pytest.mark.asyncio
async def test_js_regex_edge_cases(temp_workspace):
    """Test JS/TS heuristic parsing with comments and single quotes."""
    locales_dir = os.path.join(temp_workspace, "locales")
    js_file = os.path.join(locales_dir, "fr.js")

    complex_js = """
    // Some header comment
    export default {
        /* block comment */
        'welcome': 'Bienvenue',
        nested: {
            key: "value", // trailing comment
        },
        'extra': "L'échappement",
    };
    """
    async with aiofiles.open(js_file, "w", encoding="utf-8") as f:
        await f.write(complex_js)

    loaded = await _load_locale_data(locales_dir, "fr")
    assert loaded["welcome"] == "Bienvenue"
    assert loaded["nested"]["key"] == "value"
    assert loaded["extra"] == "L'échappement"


@pytest.mark.asyncio
async def test_path_security_enforcement(temp_workspace):
    """Test that path validation blocks access to files outside the workspace."""
    with pytest.raises(PermissionError):
        # Try to access a path outside the temp_workspace
        _validate_safe_path(
            "/etc/passwd" if os.name != "nt" else "C:\\Windows\\System32\\drivers\\etc\\hosts"
        )


@pytest.mark.asyncio
async def test_gitignore_recommendations(temp_workspace):
    """
    Test that initialize_project_config returns gitignore recommendations
    instead of modifying it.
    """
    gitignore_p = os.path.join(temp_workspace, ".gitignore")
    async with aiofiles.open(gitignore_p, "w", encoding="utf-8") as f:
        await f.write("node_modules\n")

    res = await initialize_project_config()

    async with aiofiles.open(gitignore_p, encoding="utf-8") as f:
        content = await f.read()
        # Assert file was NOT modified
        assert ".i18n-cache.json" not in content
        assert "node_modules" in content

    # Assert recommendations are in return value
    assert ".i18n-cache.json" in res["recommended_gitignore"]
    assert "!.i18n-skill.json" in res["recommended_gitignore"]


@pytest.mark.asyncio
async def test_extract_invalid_path(temp_workspace):
    """Test extraction response when scanning a non-existent file."""
    res = await extract_raw_strings("non_existent_file.vue")
    # Should not crash, but return ErrorInfo
    assert res.error is not None
    assert res.error.error_code == "PATH_ERR"
    assert "File not found" in res.error.message


@pytest.mark.asyncio
async def test_save_persona_persists_partial_update(temp_workspace):
    await initialize_project_config()

    result = await save_project_persona({"tone": "Friendly"})

    with open(os.path.join(temp_workspace, ".i18n-skill.json"), encoding="utf-8") as f:
        config = json.load(f)
    assert result == "Persona updated and saved."
    assert config["persona"]["tone"] == "Friendly"
    assert config["persona"]["domain"] == "Industrial Engineering"


@pytest.mark.asyncio
async def test_proposal_preserves_existing_ts_locale_format(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    ts_file = os.path.join(locales_dir, "zh-CN.ts")
    await _save_locale_data(ts_file, {"existing": "已有"})

    proposal = await propose_sync_i18n({"ui.title": "标题"}, "zh-CN", "Keep TS")

    assert proposal.file_path == os.path.join("locales", "zh-CN.ts")
    assert proposal.preview_file_path
    assert os.path.exists(proposal.preview_file_path)


@pytest.mark.asyncio
async def test_proposal_uses_preferred_format_for_new_locale(temp_workspace):
    config = {
        "locales_dir": "locales",
        "source_dirs": ["src"],
        "enabled_langs": ["en", "zh-CN"],
        "preferred_format": ".yml",
    }
    with open(os.path.join(temp_workspace, ".i18n-skill.json"), "w", encoding="utf-8") as f:
        json.dump(config, f)

    proposal = await propose_sync_i18n({"ui.title": "标题"}, "zh-CN", "Create YAML")

    assert proposal.file_path == os.path.join("locales", "zh-CN.yml")


@pytest.mark.asyncio
async def test_glossary_persists_updates_and_status(temp_workspace):
    first = await update_project_glossary("Dashboard", "仪表盘")
    glossary_path = os.path.join(temp_workspace, "GLOSSARY.json")
    with open(glossary_path, encoding="utf-8") as f:
        saved = json.load(f)
    saved["rules"]["forbidden_terms"] = ["控制台"]
    with open(glossary_path, "w", encoding="utf-8") as f:
        json.dump(saved, f)

    second = await update_project_glossary("Dashboard", "面板")
    loaded = await load_project_glossary()
    status = await check_project_status()

    assert first == "Learned"
    assert second == "Learned"
    assert len(loaded["glossary"]) == 1
    assert loaded["glossary"][0]["translation"] == "面板"
    assert loaded["rules"]["forbidden_terms"] == ["控制台"]
    assert status.has_glossary is True


@pytest.mark.asyncio
async def test_status_includes_vcs_info_when_available(temp_workspace, monkeypatch):
    expected_vcs = {
        "branch": "main",
        "commit_hash": "deadbee",
        "uncommitted_changes_count": 2,
        "is_dirty": True,
    }
    monkeypatch.setattr(tools, "get_vcs_status", lambda _root: expected_vcs)

    status = await check_project_status()

    assert status.vcs_info == expected_vcs
