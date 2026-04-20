import shutil
import tempfile

import pytest

from i18n_agent_skill.snapshot import TranslationSnapshotManager


@pytest.fixture
def temp_workspace():
    """创建一个临时工作区进行快照测试"""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_snapshot_regression_alert(temp_workspace):
    """测试分值下降触发回归告警"""
    manager = TranslationSnapshotManager(temp_workspace)
    key = "common.save"

    # 1. 存入一个高分翻译 (10分)
    await manager.update_snapshot(key, "保存设置", 10)

    # 2. 检查一个低分翻译 (7分)
    result = await manager.check_regression(key, 7)
    assert result is not None
    assert result.is_degraded is True
    assert result.snapshot_score == 10
    assert result.current_score == 7


@pytest.mark.asyncio
async def test_snapshot_improvement(temp_workspace):
    """测试分值上升不触发告警且支持快照更新"""
    manager = TranslationSnapshotManager(temp_workspace)
    key = "common.delete"

    # 1. 存入一个低分翻译 (5分)
    await manager.update_snapshot(key, "删掉", 5)

    # 2. 检查一个高分翻译 (9分)
    result = await manager.check_regression(key, 9)
    assert result is None  # 不应告警

    # 3. 更新快照后再次检查
    await manager.update_snapshot(key, "确认删除", 9)
    # 此时快照分应已升至 9，再次传入 7 分则应告警
    result_degraded = await manager.check_regression(key, 7)
    assert result_degraded.snapshot_score == 9
