import shutil
import tempfile

import pytest

from i18n_agent_skill.snapshot import TranslationSnapshotManager


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for snapshot testing."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_snapshot_regression_alert(temp_workspace):
    """Test that regression alarm triggers when score decreases."""
    manager = TranslationSnapshotManager(temp_workspace)
    key = "button.save"

    # 1. Store a high-score translation (10)
    await manager.update_snapshot(key, "Save Settings", 10)

    # 2. Check a low-score translation (7)
    result = await manager.check_regression(key, 7)

    assert result is not None
    assert result.is_degraded is True
    assert result.snapshot_score == 10
    assert "Quality Regression Warning" in result.warning_message


@pytest.mark.asyncio
async def test_snapshot_update_flow(temp_workspace):
    """Test that score increase doesn't trigger alarm and allows snapshot update."""
    manager = TranslationSnapshotManager(temp_workspace)
    key = "button.delete"

    # 1. Store a low-score translation (5)
    await manager.update_snapshot(key, "Del", 5)

    # 2. Check a high-score translation (9)
    result = await manager.check_regression(key, 9)
    assert result is None  # Should not warn

    # 3. Update snapshot and re-check
    await manager.update_snapshot(key, "Confirm Delete", 9)

    # Now snapshot score is 9, check with 7 should warn
    result_degraded = await manager.check_regression(key, 7)
    assert result_degraded is not None
    assert result_degraded.snapshot_score == 9
