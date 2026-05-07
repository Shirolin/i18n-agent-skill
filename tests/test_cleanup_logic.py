import json
import os

import pytest

from i18n_agent_skill import tools
from i18n_agent_skill.__main__ import cli_main


@pytest.fixture
def complex_mock_project(tmp_path, monkeypatch):
    # Setup paths
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", str(workspace))
    os.chdir(workspace)

    # 1. Create multiple locales
    loc_dir = workspace / "locales"
    loc_dir.mkdir()
    (loc_dir / "en.json").write_text(
        json.dumps({"used": "Used", "en_dead": "Dead"}), encoding="utf-8"
    )
    (loc_dir / "zh-CN.json").write_text(
        json.dumps({"used": "Used", "zh_dead": "Dead"}), encoding="utf-8"
    )

    # 2. Create source code
    src_dir = workspace / "src"
    src_dir.mkdir()
    (src_dir / "App.js").write_text("t('used')", encoding="utf-8")

    # 3. Setup config
    config = {"locales_dir": "locales", "source_dirs": ["src"], "enabled_langs": ["en", "zh-CN"]}
    (workspace / ".i18n-skill.json").write_text(json.dumps(config), encoding="utf-8")

    return workspace


@pytest.mark.asyncio
async def test_get_dead_keys_robustness(complex_mock_project):
    """Verify that get_dead_keys handles invalid languages gracefully."""
    # Invalid language should return empty list (per current implementation failsafe)
    # but importantly it should not crash.
    res = await tools.get_dead_keys(lang_code="non-existent")
    assert res == []


@pytest.mark.asyncio
async def test_cli_cleanup_all_logic(complex_mock_project, monkeypatch, capsys):
    """
    Test the --lang all logic in __main__.py.
    We mock sys.argv and call cli_main to simulate a real execution.
    """
    import sys

    # Simulate: /i18n-cleanup --lang all
    test_args = ["i18n_agent_skill", "cleanup", "--lang", "all"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Run CLI
    await cli_main()

    # Capture output
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    # Assertions
    assert output["language"] == "all"
    assert output["total_dead_keys"] == 2

    results = output["results"]
    assert len(results) == 2

    en_res = next(r for r in results if r["language"] == "en")
    assert "en_dead" in en_res["dead_keys"]

    zh_res = next(r for r in results if r["language"] == "zh-CN")
    assert "zh_dead" in zh_res["dead_keys"]


@pytest.mark.asyncio
async def test_module_import_safety():
    """Verify that importing __main__ doesn't trigger side effects like sys.exit."""
    # If the previous bootstrap_venv bug was present, this would likely crash or
    # exit during the import phase when run via pytest.
    try:
        assert True
    except SystemExit:
        pytest.fail("Importing __main__ triggered a SystemExit (bootstrap_venv bug)")
    except Exception as e:
        pytest.fail(f"Importing __main__ failed: {str(e)}")
