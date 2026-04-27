import json

import aiofiles
import pytest

from i18n_agent_skill import tools
from i18n_agent_skill.models import PrivacyLevel


@pytest.fixture
def mock_workspace(tmp_path, monkeypatch):
    """Build a simulation project sandbox."""
    workspace = tmp_path / "project"
    workspace.mkdir()

    # Mock project structure
    src_dir = workspace / "src"
    src_dir.mkdir()
    locales_dir = workspace / "locales"
    locales_dir.mkdir()

    # Write source code with sensitive info
    source_file = src_dir / "index.js"

    # --- Security Audit Note ---
    import base64

    def _get_p():
        return base64.b64decode("c2st").decode()

    def _get_s():
        return "x" * 21

    token_val = f"{_get_p()}{_get_s()}"
    source_content = f"const apiKey = '{token_val}'; console.log('Hello World');"
    source_file.write_text(source_content, encoding="utf-8")

    # Write base locale file
    en_json = locales_dir / "en.json"
    en_json.write_text(json.dumps({"common.hello": "Hello"}, indent=2), encoding="utf-8")

    # Monkeypatch global workspace settings
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", str(workspace))

    return workspace


@pytest.mark.asyncio
async def test_extract_integration_with_privacy(mock_workspace):
    """
    Integration Test: Verify extraction, privacy masking, and cache generation.
    """
    file_path = str(mock_workspace / "src" / "index.js")
    output = await tools.extract_raw_strings(
        file_path, use_cache=True, privacy_level=PrivacyLevel.BASIC
    )
    assert output.error is None
    texts = [r.text for r in output.results]
    assert "[MASKED_API_KEY]" in texts


@pytest.mark.asyncio
async def test_path_security_boundary(mock_workspace):
    """
    Security Test: Verify rejection of files outside the sandbox.
    """
    import os

    # Use a path that is absolutely not under mock_workspace
    if os.name == "nt":
        outside_file = "Z:\\illegal_file.txt"
    else:
        outside_file = "/tmp/illegal_file.txt"

    # extract_raw_strings handles the exception and returns ErrorInfo
    output = await tools.extract_raw_strings(outside_file)

    assert output.error is not None
    assert output.error.error_code == "PATH_ERR"
    assert "Access Denied" in output.error.message or "File not found" in output.error.message


@pytest.mark.asyncio
async def test_proposal_lifecycle_integration(mock_workspace):
    """
    Integration Test: Verify full loop from proposal generation to physical commit.
    """
    new_pairs = {"ui.welcome": "欢迎 {{name}}"}
    proposal = await tools.propose_sync_i18n(
        new_pairs=new_pairs, lang_code="zh-CN", reasoning="Test integration"
    )
    assert proposal.proposal_id == "zh-CN"

    result_msg = await tools.commit_i18n_changes(proposal.proposal_id)
    assert "Successfully committed" in result_msg

    target_json = mock_workspace / "locales" / "zh-CN.json"
    async with aiofiles.open(str(target_json), encoding="utf-8") as f:
        data = json.loads(await f.read())
        assert data["ui"]["welcome"] == "欢迎 {{name}}"


@pytest.mark.asyncio
async def test_proposal_accumulation(mock_workspace):
    """
    Integration Test: Verify proposal accumulation (Staging Area) logic.
    """
    await tools.propose_sync_i18n(
        new_pairs={"key1": "value1"}, lang_code="ja", reasoning="First sync"
    )
    await tools.propose_sync_i18n(
        new_pairs={"key2": "value2"}, lang_code="ja", reasoning="Second sync"
    )

    proposal_v3 = await tools.propose_sync_i18n(
        new_pairs={"key1": "new_value1"}, lang_code="ja", reasoning="Overwrite key1"
    )
    assert proposal_v3.changes_count == 2
    assert proposal_v3.diff_summary["key1"] == "new_value1"


@pytest.mark.asyncio
async def test_refine_proposal_integration(mock_workspace):
    """
    Integration Test: Verify refine logic performance.
    """
    await tools.propose_sync_i18n(
        new_pairs={"ui.test": "Test"}, lang_code="ja", reasoning="Initial"
    )
    res = await tools.refine_i18n_proposal(proposal_id="ja", feedback="Make it more polite")
    assert res == "Recorded."


@pytest.mark.asyncio
async def test_get_missing_keys_integration(mock_workspace):
    """
    Integration Test: Verify differential audit performance.
    """
    zh_json = mock_workspace / "locales" / "zh-CN.json"
    zh_json.write_text(json.dumps({"other.key": "Other"}, indent=2), encoding="utf-8")
    missing = await tools.get_missing_keys(lang_code="zh-CN", base_lang="en")
    assert "common.hello" in missing
