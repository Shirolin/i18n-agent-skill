import json
from pathlib import Path

import pytest

from i18n_agent_skill import tools
from i18n_agent_skill.__main__ import cli_main


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture
def optimize_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", str(workspace))

    _write_json(workspace / "src" / "locales" / "en.json", {"app": {"title": "Hello"}})
    _write_json(workspace / "src" / "locales" / "zh_CN.json", {"app": {"title": "你好"}})
    _write_json(
        workspace / ".i18n-skill.json",
        {
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
        },
    )
    return workspace


@pytest.mark.asyncio
async def test_optimize_artifact_is_self_describing(optimize_workspace):
    result = await tools.optimize_translations("zh_CN")

    assert result["artifact_type"] == "optimize_task"
    assert result["do_not_sync_directly"] is True
    assert result["summary"]["language"] == "zh_CN"
    assert result["summary"]["target_count"] == 1
    assert result["summary"]["glossary_count"] == 0
    assert result["summary"]["changes_count"] == 1
    assert result["pending_confirmation"]
    assert result["cleanup"]["temporary_files"] == [result["task_file_path"]]
    assert result["cleanup"]["safe_to_delete_now"] is False
    assert result["proceed"]["requires_confirmation"] is True
    assert result["proceed"]["ready_for_sync"] is False
    assert result["next_steps"]

    task_file = Path(result["task_file_path"])
    task_data = json.loads(task_file.read_text(encoding="utf-8"))
    assert task_data["artifact_type"] == "optimize_task"
    assert task_data["do_not_sync_directly"] is True
    assert task_data["summary"]["changes_count"] == 1
    assert task_data["pending_confirmation"]
    assert task_data["cleanup"]["temporary_files"] == [result["task_file_path"]]
    assert task_data["proceed"]["requires_confirmation"] is True
    assert "targets" in task_data


@pytest.mark.asyncio
async def test_sync_rejects_optimize_task_file_without_mutating_locale(
    optimize_workspace, monkeypatch, capsys
):
    import sys

    optimize_result = await tools.optimize_translations("zh_CN")
    locale_before = (optimize_workspace / "src" / "locales" / "zh_CN.json").read_text(
        encoding="utf-8"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "i18n_agent_skill",
            "sync",
            "--lang",
            "zh_CN",
            "--data",
            optimize_result["task_file_path"],
        ],
    )
    await cli_main()

    output = json.loads(capsys.readouterr().out)
    assert output["error_code"] == "INVALID_SYNC_INPUT"
    assert output["artifact_type"] == "optimize_task"
    assert "cannot be passed directly to sync" in output["error"]
    assert output["next_steps"]

    locale_after = (optimize_workspace / "src" / "locales" / "zh_CN.json").read_text(
        encoding="utf-8"
    )
    assert locale_after == locale_before
    assert not (optimize_workspace / ".i18n-proposals" / "proposal_zh_CN.json").exists()


@pytest.mark.asyncio
async def test_sync_accepts_plain_key_value_file(optimize_workspace, monkeypatch, capsys):
    import sys

    payload_path = optimize_workspace / "temp" / "plain_sync_payload.json"
    _write_json(payload_path, {"app.title": "新的标题"})

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "i18n_agent_skill",
            "sync",
            "--lang",
            "zh_CN",
            "--data",
            str(payload_path),
        ],
    )
    await cli_main()

    output = json.loads(capsys.readouterr().out)
    assert output["proposal_id"] == "zh_CN"
    assert output["preview_file_path"]
    assert (optimize_workspace / ".i18n-proposals" / "proposal_zh_CN.json").exists()


@pytest.mark.asyncio
async def test_optimize_without_targets_returns_noop_confirmation_and_cleanup(
    optimize_workspace,
):
    snapshot_mgr = tools.TranslationSnapshotManager(str(optimize_workspace))
    await snapshot_mgr.update_snapshot(
        "app.title", "你好", 10, status=tools.TranslationStatus.APPROVED
    )

    result = await tools.optimize_translations("zh_CN")

    assert result["summary"]["target_count"] == 0
    assert result["summary"]["glossary_count"] == 1
    assert result["summary"]["changes_count"] == 0
    assert result["pending_confirmation"] == []
    assert result["proceed"]["requires_confirmation"] is False
    assert result["proceed"]["ready_for_sync"] is False
    assert result["cleanup"]["safe_to_delete_now"] is True
    assert any("No optimization targets" in step for step in result["next_steps"])

    task_data = json.loads(Path(result["task_file_path"]).read_text(encoding="utf-8"))
    assert task_data["pending_confirmation"] == []
    assert task_data["cleanup"]["safe_to_delete_now"] is True
