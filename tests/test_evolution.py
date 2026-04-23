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
    # 模拟项目结构
    os.makedirs(os.path.join(test_dir, "locales"))
    set_workspace_root(test_dir)
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_generate_quality_report(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    lang_file = os.path.join(locales_dir, "zh-CN.json")

    # 模拟 3 条词条：1 条 APPROVED, 2 条 DRAFT
    data = {"k1": "v1", "k2": "v2", "k3": "v3"}
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    manager = TranslationSnapshotManager(temp_workspace)
    await manager.update_snapshot("k1", "v1", 10, status=TranslationStatus.APPROVED)

    # 生成报告
    report = await generate_quality_report("zh-CN")

    assert report.total_keys == 3
    assert report.approved_keys == 1
    # 争议项（待审项）应包含 2 条 DRAFT 词条
    assert len(report.controversial_items) == 2
    assert report.controversial_items[0].key in ["k2", "k3"]


@pytest.mark.asyncio
async def test_reference_optimize_translations(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")

    # 准备环境：Base(en), Pivot(zh-CN), Target(ja)
    en_data = {"login.submit": "Submit"}
    zh_data = {"login.submit": "登录"}  # 修正后的地道中文
    ja_data = {"login.submit": "送信"}  # 原始的不地道日文

    for lang, data in [("en", en_data), ("zh-CN", zh_data), ("ja", ja_data)]:
        with open(os.path.join(locales_dir, f"{lang}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    # 标记中文为 APPROVED（作为语义基准）
    manager = TranslationSnapshotManager(temp_workspace)
    await manager.update_snapshot("login.submit", "登录", 10, status=TranslationStatus.APPROVED)

    # 执行参照优化（用中文基准去修日文）
    opt_result = await reference_optimize_translations(pivot_lang="zh-CN", target_lang="ja")

    assert "login.submit" in opt_result["targets"]
    # 验证是否正确提取了参考语义
    target_item = opt_result["targets"]["login.submit"]
    assert target_item["base_context"] == "Submit"
    assert target_item["reference_mapping"] == "登录"
    assert target_item["current"] == "送信"


@pytest.mark.asyncio
async def test_translation_status_flow(temp_workspace):
    manager = TranslationSnapshotManager(temp_workspace)
    key = "test.key"

    # 1. 默认状态应为 DRAFT
    assert await manager.get_status(key) == TranslationStatus.DRAFT

    # 2. 更新为 APPROVED
    await manager.update_snapshot(key, "翻译值", 10, status=TranslationStatus.APPROVED)
    assert await manager.get_status(key) == TranslationStatus.APPROVED


@pytest.mark.asyncio
async def test_sync_manual_modifications(temp_workspace):
    # 准备环境
    locales_dir = os.path.join(temp_workspace, "locales")
    lang_file = os.path.join(locales_dir, "zh-CN.json")

    # 初始化一个翻译文件
    initial_data = {"login": {"title": "登录"}}
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    # 此时快照中没有任何记录，同步应该能检测到并标记为 APPROVED
    result = await sync_manual_modifications("zh-CN")
    assert "Learned 1" in result

    manager = TranslationSnapshotManager(temp_workspace)
    assert await manager.get_status("login.title") == TranslationStatus.APPROVED

    # 手动修改内容
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

    # 准备数据：一个已确认，一个待定
    data = {"nav": {"home": "首页"}, "button": {"submit": "提交"}}
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    manager = TranslationSnapshotManager(temp_workspace)
    # 将 nav.home 标记为 APPROVED
    await manager.update_snapshot("nav.home", "首页", 10, status=TranslationStatus.APPROVED)
    # 将 button.submit 标记为 DRAFT
    await manager.update_snapshot("button.submit", "提交", 5, status=TranslationStatus.DRAFT)

    # 执行优化筛选
    opt_result = await optimize_translations("zh-CN")

    # 首页应在术语表中
    assert "nav.home" in opt_result["dynamic_glossary"]
    # 提交应在待优化列表中
    assert "button.submit" in opt_result["targets"]
    assert "nav.home" not in opt_result["targets"]
