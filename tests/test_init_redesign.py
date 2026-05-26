import json
import os
import shutil
import tempfile

import pytest

from i18n_agent_skill import tools


def _write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@pytest.fixture
def workspace(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", tmp_dir)
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.mark.asyncio
async def test_init_sync_detects_existing_languages(workspace):
    locale_dir = os.path.join(workspace, "src", "locales")
    _write_json(os.path.join(locale_dir, "en.json"), {"k": "v"})
    _write_json(os.path.join(locale_dir, "zh_CN.json"), {"k": "值"})
    _write_json(os.path.join(locale_dir, "zh_TW.json"), {"k": "值"})
    _write_json(os.path.join(locale_dir, "fr.json"), {"k": "v"})
    _write_json(os.path.join(locale_dir, "ja.json"), {"k": "v"})

    result = await tools.initialize_project_config()

    assert result["mode"] == "sync"
    assert result["config"]["locales_dir"] == "src/locales"
    assert result["config"]["enabled_langs"] == ["en", "fr", "ja", "zh_CN", "zh_TW"]


@pytest.mark.asyncio
async def test_init_migrates_stale_zh_config(workspace):
    locale_dir = os.path.join(workspace, "src", "locales")
    _write_json(os.path.join(locale_dir, "en.json"), {"k": "v"})
    _write_json(os.path.join(locale_dir, "zh_CN.json"), {"k": "值"})
    _write_json(os.path.join(locale_dir, "zh_TW.json"), {"k": "值"})
    _write_json(
        os.path.join(workspace, ".i18n-skill.json"),
        {
            "source_dirs": ["src"],
            "locales_dir": "locales",
            "enabled_langs": ["en", "zh"],
            "privacy_level": "basic",
        },
    )

    result = await tools.initialize_project_config()

    assert result["mode"] == "sync"
    assert result["config"]["enabled_langs"] == ["en", "zh_CN", "zh_TW"]
    assert any("stale language code 'zh'" in item for item in result["migrations"])


@pytest.mark.asyncio
async def test_init_repairs_wrong_locales_dir_when_single_candidate(workspace):
    locale_dir = os.path.join(workspace, "src", "locales")
    _write_json(os.path.join(locale_dir, "en.json"), {"k": "v"})
    _write_json(
        os.path.join(workspace, ".i18n-skill.json"),
        {
            "source_dirs": ["src"],
            "locales_dir": "locales",
            "enabled_langs": ["en"],
            "privacy_level": "basic",
        },
    )

    result = await tools.initialize_project_config()

    assert result["mode"] == "sync"
    assert result["config"]["locales_dir"] == "src/locales"


@pytest.mark.asyncio
async def test_init_enters_reconcile_for_multiple_roots(workspace):
    _write_json(os.path.join(workspace, "src", "locales", "en.json"), {"k": "v"})
    _write_json(os.path.join(workspace, "public", "locales", "en.json"), {"k": "v"})

    result = await tools.initialize_project_config()

    assert result["mode"] == "reconcile"
    assert result["requires_confirmation"] is True
    assert not os.path.exists(os.path.join(workspace, ".i18n-skill.json"))


@pytest.mark.asyncio
async def test_init_bootstrap_without_locale_assets(workspace):
    os.makedirs(os.path.join(workspace, "src"), exist_ok=True)
    with open(os.path.join(workspace, "src", "main.ts"), "w", encoding="utf-8") as f:
        f.write("console.log('hello')")

    result = await tools.initialize_project_config()

    assert result["mode"] == "bootstrap"
    assert result["config"]["enabled_langs"] == ["en"]
    assert result["config"]["locales_dir"] == "src/locales"


@pytest.mark.asyncio
async def test_init_unsupported_when_locale_filenames_are_not_languages(workspace):
    _write_json(os.path.join(workspace, "locales", "common.json"), {"k": "v"})

    result = await tools.initialize_project_config()

    assert result["mode"] == "unsupported"
    assert not os.path.exists(os.path.join(workspace, ".i18n-skill.json"))


@pytest.mark.asyncio
async def test_init_hard_fail_on_malformed_config(workspace):
    config_path = os.path.join(workspace, ".i18n-skill.json")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("{bad-json")

    result = await tools.initialize_project_config()

    assert result["mode"] == "hard_fail"
    with open(config_path, encoding="utf-8") as f:
        assert f.read() == "{bad-json"


@pytest.mark.asyncio
async def test_init_preserves_user_fields_during_sync(workspace):
    _write_json(os.path.join(workspace, "src", "locales", "en.json"), {"k": "v"})
    _write_json(os.path.join(workspace, "src", "locales", "de.json"), {"k": "v"})
    _write_json(
        os.path.join(workspace, ".i18n-skill.json"),
        {
            "source_dirs": ["src"],
            "ignore_dirs": ["node_modules", "dist", "custom"],
            "locales_dir": "locales",
            "enabled_langs": ["en", "zh"],
            "privacy_level": "strict",
            "persona": {"domain": "Ecom", "audience": "Ops", "tone": "Direct"},
            "ignored_strings": ["React"],
            "protected_lang_key_patterns": ["^brand\\."],
            "locale_file_pattern": ".*",
        },
    )

    result = await tools.initialize_project_config()
    config = result["config"]

    assert result["mode"] == "sync"
    assert config["privacy_level"] == "strict"
    assert config["persona"]["domain"] == "Ecom"
    assert config["ignored_strings"] == ["React"]
    assert config["protected_lang_key_patterns"] == ["^brand\\."]
    assert config["ignore_dirs"] == ["node_modules", "dist", "custom"]
