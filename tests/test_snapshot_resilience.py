import os
import pytest
import aiofiles
from i18n_agent_skill.snapshot import TranslationSnapshotManager
from i18n_agent_skill.models import TranslationStatus

@pytest.fixture
def temp_ws(tmp_path):
    return str(tmp_path)

@pytest.mark.asyncio
async def test_snapshot_corruption_resilience(temp_ws):
    """Verify that the manager handles corrupted JSON files without crashing."""
    mgr = TranslationSnapshotManager(temp_ws)
    
    # 1. Create a corrupted (invalid JSON) snapshot file
    async with aiofiles.open(mgr.path, "w", encoding="utf-8") as f:
        await f.write("INVALID_JSON_DATA_!!!")
    
    # 2. Try to read status (should fallback to empty dict and return DRAFT)
    status = await mgr.get_status("any_key")
    assert status == TranslationStatus.DRAFT

@pytest.mark.asyncio
async def test_snapshot_empty_file_resilience(temp_ws):
    """Verify that the manager handles empty snapshot files."""
    mgr = TranslationSnapshotManager(temp_ws)
    
    # 1. Create an empty snapshot file
    async with aiofiles.open(mgr.path, "w", encoding="utf-8") as f:
        await f.write("")
    
    # 2. Try to read status
    status = await mgr.get_status("any_key")
    assert status == TranslationStatus.DRAFT

@pytest.mark.asyncio
async def test_snapshot_write_after_corruption(temp_ws):
    """Verify that we can still write to a file after it was corrupted."""
    mgr = TranslationSnapshotManager(temp_ws)
    
    # 1. Corrupt the file
    async with aiofiles.open(mgr.path, "w", encoding="utf-8") as f:
        await f.write("CORRUPTED")
        
    # 2. Perform an update
    await mgr.update_snapshot("key1", "val1", 10, TranslationStatus.APPROVED)
    
    # 3. Verify it's now valid JSON and contains the data
    new_status = await mgr.get_status("key1")
    assert new_status == TranslationStatus.APPROVED
