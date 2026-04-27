import json
import os
import shutil
import tempfile

import pytest

from i18n_agent_skill.models import TranslationStatus
from i18n_agent_skill.snapshot import TranslationSnapshotManager
from i18n_agent_skill.tools import (
    generate_quality_report,
    optimize_translations,
    reference_optimize_translations,
    set_workspace_root,
    sync_manual_modifications,
)


@pytest.fixture
def temp_workspace():
    test_dir = tempfile.mkdtemp()
    # Mock project structure
    os.makedirs(os.path.join(test_dir, "locales"))
    set_workspace_root(test_dir)
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_generate_quality_report(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    lang_file = os.path.join(locales_dir, "zh-CN.json")

    # Mock 3 entries: 1 APPROVED, 2 DRAFT (one with typography error triggering Linter)
    data = {"k1": "v1", "k2": "中文和english没有空格", "k3": "v3"}
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    manager = TranslationSnapshotManager(temp_workspace)
    await manager.update_snapshot("k1", "v1", 10, status=TranslationStatus.APPROVED)

    # Generate report
    report = await generate_quality_report("zh-CN")

    assert report.total_keys == 3
    assert report.approved_keys == 1
    # Controversial items should only include k2 (due to Linter error)
    # k3 is DRAFT but doesn't violate style rules, so current logic might skip it
    # depending on whether we want to audit ALL drafts or just style-violating ones.
    # Currently tools.py only adds style violations to controversial_items.
    assert len(report.controversial_items) == 1
    assert report.controversial_items[0].key == "k2"


@pytest.mark.asyncio
async def test_generate_quality_report_variable_mismatch(temp_workspace):
    """Test that quality report flags mismatched placeholders."""
    locales_dir = os.path.join(temp_workspace, "locales")

    # 1. Base has {name}
    with open(os.path.join(locales_dir, "en.json"), "w", encoding="utf-8") as f:
        json.dump({"greeting": "Hello, {name}!"}, f)

    # 2. Target has {username} (Mismatch!)
    with open(os.path.join(locales_dir, "zh-CN.json"), "w", encoding="utf-8") as f:
        json.dump({"greeting": "你好，{username}！"}, f)

    report = await generate_quality_report("zh-CN")

    # Verify the mismatch is flagged
    mismatches = [
        item for item in report.controversial_items if item.issue_type == "VARIABLE_MISMATCH"
    ]
    assert len(mismatches) == 1
    assert mismatches[0].key == "greeting"
    assert "{name}" in mismatches[0].reasoning
    assert "{username}" in mismatches[0].reasoning


@pytest.mark.asyncio
async def test_reference_optimize_translations(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")

    # Setup environment: Base(en), Pivot(zh-CN), Target(ja)
    en_data = {"login.submit": "Submit"}
    zh_data = {"login.submit": "登录"}  # Polished Chinese
    ja_data = {"login.submit": "送信"}  # Original Japanese

    for lang, data in [("en", en_data), ("zh-CN", zh_data), ("ja", ja_data)]:
        with open(os.path.join(locales_dir, f"{lang}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    # Mark Chinese as APPROVED (as semantic baseline)
    manager = TranslationSnapshotManager(temp_workspace)
    await manager.update_snapshot("login.submit", "登录", 10, status=TranslationStatus.APPROVED)

    # Perform reference optimization (Fix ja using zh-CN mapping)
    opt_result = await reference_optimize_translations(pivot_lang="zh-CN", target_lang="ja")

    assert "login.submit" in opt_result["targets"]
    target_item = opt_result["targets"]["login.submit"]
    assert target_item["base_context"] == "Submit"
    assert target_item["reference_mapping"] == "登录"
    assert target_item["current"] == "送信"


@pytest.mark.asyncio
async def test_translation_status_flow(temp_workspace):
    manager = TranslationSnapshotManager(temp_workspace)
    key = "test.key"

    # 1. Default status should be DRAFT
    assert await manager.get_status(key) == TranslationStatus.DRAFT

    # 2. Update to APPROVED
    await manager.update_snapshot(key, "Value", 10, status=TranslationStatus.APPROVED)
    assert await manager.get_status(key) == TranslationStatus.APPROVED


@pytest.mark.asyncio
async def test_sync_manual_modifications(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    lang_file = os.path.join(locales_dir, "zh-CN.json")

    initial_data = {"login": {"title": "登录"}}
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    # Initial sync should detect and mark as APPROVED
    result = await sync_manual_modifications("zh-CN")
    assert "Learned 1" in result

    manager = TranslationSnapshotManager(temp_workspace)
    assert await manager.get_status("login.title") == TranslationStatus.APPROVED

    # Manual modification
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump({"login": {"title": "进入系统"}}, f)

    result = await sync_manual_modifications("zh-CN")
    assert "Learned 1" in result
    snapshots = await manager._read_snapshots()
    assert snapshots["login.title"]["translation"] == "进入系统"


@pytest.mark.asyncio
async def test_optimize_translations_filtering(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    lang_file = os.path.join(locales_dir, "zh-CN.json")

    data = {"nav": {"home": "首页"}, "button": {"submit": "提交"}}
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    manager = TranslationSnapshotManager(temp_workspace)
    await manager.update_snapshot("nav.home", "首页", 10, status=TranslationStatus.APPROVED)
    await manager.update_snapshot("button.submit", "提交", 5, status=TranslationStatus.DRAFT)

    opt_result = await optimize_translations("zh-CN")

    # Access the task file created by tools.py
    task_path = opt_result["task_file_path"]
    with open(task_path, encoding="utf-8") as f:
        task_data = json.load(f)

    # Home should be in glossary
    assert "nav.home" in task_data["dynamic_glossary"]
    # Submit should be in targets
    assert "button.submit" in task_data["targets"]
    assert "nav.home" not in task_data["targets"]
