import os
import pytest
import tempfile
import shutil
import json
from i18n_agent_skill import tools

@pytest.fixture
def temp_workspace(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    original_root = tools.WORKSPACE_ROOT
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", tmp_dir)
    yield tmp_dir
    shutil.rmtree(tmp_dir)

@pytest.mark.asyncio
async def test_load_ts_locale_with_urls(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    os.makedirs(locales_dir)
    
    ts_content = """
    export default {
        "api_url": "https://api.example.com/v1",
        "description": "Text with // content",
        "nested": {
            "link": "ftp://files.com"
        }
    };
    """
    ts_path = os.path.join(locales_dir, "en.ts")
    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(ts_content)
        
    data = await tools._load_locale_data(locales_dir, "en")
    assert data["api_url"] == "https://api.example.com/v1"
    assert data["description"] == "Text with // content"
    assert data["nested"]["link"] == "ftp://files.com"

@pytest.mark.asyncio
async def test_load_js_locale_commonjs(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    os.makedirs(locales_dir)
    
    js_content = """
    module.exports = {
        "key": "value // not a comment"
    };
    """
    js_path = os.path.join(locales_dir, "en.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
        
    data = await tools._load_locale_data(locales_dir, "en")
    assert data["key"] == "value // not a comment"

@pytest.mark.asyncio
async def test_load_ts_locale_with_comments(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    os.makedirs(locales_dir)
    
    ts_content = """
    // Top comment
    export default {
        /* Inline comment */
        "key": "val" // EOL comment
    };
    """
    ts_path = os.path.join(locales_dir, "en.ts")
    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(ts_content)
        
    data = await tools._load_locale_data(locales_dir, "en")
    assert data["key"] == "val"
