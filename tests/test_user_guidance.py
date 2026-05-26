import json
from pathlib import Path

import pytest

from i18n_agent_skill import tools
from i18n_agent_skill.__main__ import cli_main


@pytest.fixture
def guidance_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", str(workspace))
    return workspace


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.asyncio
async def test_init_sync_includes_actionable_next_steps(guidance_workspace):
    _write_json(guidance_workspace / "src" / "locales" / "en.json", {"app": {"title": "Hello"}})
    _write_json(
        guidance_workspace / "src" / "locales" / "zh_CN.json",
        {"app": {"title": "你好"}},
    )

    result = await tools.initialize_project_config()

    assert result["mode"] == "sync"
    assert result["suggested_action"]
    assert "status" in " ".join(result["next_steps"])
    assert "audit --lang all" in " ".join(result["next_steps"])
    assert "scan --vcs" in " ".join(result["next_steps"])


@pytest.mark.asyncio
async def test_init_bootstrap_guides_user_to_create_base_locale(guidance_workspace):
    src_dir = guidance_workspace / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.ts").write_text("console.log('hello')", encoding="utf-8")

    result = await tools.initialize_project_config()

    assert result["mode"] == "bootstrap"
    assert any("Create" in step for step in result["next_steps"])
    assert any("base locale file" in step for step in result["next_steps"])


@pytest.mark.asyncio
async def test_init_reconcile_blocks_follow_on_actions_until_confirmed(guidance_workspace):
    _write_json(guidance_workspace / "src" / "locales" / "en.json", {"k": "v"})
    _write_json(guidance_workspace / "public" / "locales" / "en.json", {"k": "v"})

    result = await tools.initialize_project_config()

    assert result["mode"] == "reconcile"
    assert result["requires_confirmation"] is True
    assert any("Do not run audit or sync yet" in step for step in result["next_steps"])


@pytest.mark.asyncio
async def test_audit_all_includes_coverage_summary_and_noise_notice(
    guidance_workspace, monkeypatch, capsys
):
    import sys

    _write_json(guidance_workspace / "src" / "locales" / "en.json", {"used": "Used"})
    _write_json(guidance_workspace / "src" / "locales" / "zh_CN.json", {"used": "已使用"})
    config = {
        "source_dirs": ["src"],
        "ignore_dirs": ["node_modules", "dist", ".git", ".venv"],
        "locales_dir": "src/locales",
        "enabled_langs": ["en", "zh_CN"],
        "privacy_level": "basic",
        "persona": {
            "domain": "Industrial Engineering",
            "audience": "Developers",
            "tone": "Technical",
            "custom_guidelines": [],
        },
        "protected_lang_key_patterns": [],
        "ignored_keys": [],
        "ignored_strings": [],
        "preferred_format": ".json",
        "locale_file_pattern": None,
    }
    _write_json(guidance_workspace / ".i18n-skill.json", config)
    src_dir = guidance_workspace / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "App.tsx").write_text("const label = 'Needs extraction';", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["i18n_agent_skill", "audit", "--lang", "all"])
    await cli_main()

    output = json.loads(capsys.readouterr().out)
    assert "coverage_summary" in output
    assert output["coverage_summary"]["base_language"] == "en"
    assert "noise_notice" in output
    assert output["next_steps"]


def test_docs_no_longer_advertise_fake_one_step_entrypoint():
    repo_root = Path(__file__).resolve().parents[1]
    docs = [
        repo_root / "README.md",
        repo_root / "README.zh-CN.md",
        repo_root / "SKILL.md",
    ]

    for doc_path in docs:
        content = doc_path.read_text(encoding="utf-8")
        assert "./i18n init --auto" not in content
        assert "/i18n-fix" not in content
        assert (
            "do not run ad-hoc deletion scripts" in content.lower()
            or "禁止直接运行临时删除脚本" in content
        )
        assert (
            "must not be passed directly to `sync`" in content
            or "不能直接传给 `sync`" in content
        )
