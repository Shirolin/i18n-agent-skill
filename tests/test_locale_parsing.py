import os
import pytest
import tempfile
import shutil
import json
import yaml
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
        
@pytest.mark.asyncio
async def test_load_yaml_locale(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    os.makedirs(locales_dir)
    
    yaml_content = """
    common:
      welcome: "Welcome to YAML"
      nested:
        key: "value"
    """
    yaml_path = os.path.join(locales_dir, "en.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
        
    data = await tools._load_locale_data(locales_dir, "en")
    assert data["common"]["welcome"] == "Welcome to YAML"
    assert data["common"]["nested"]["key"] == "value"

@pytest.mark.asyncio
async def test_save_yaml_locale(temp_workspace):
    locales_dir = os.path.join(temp_workspace, "locales")
    os.makedirs(locales_dir)
    
    data = {"ui": {"title": "Hello YAML"}}
    yaml_path = os.path.join(locales_dir, "en.yml")
    
    await tools._save_locale_data(yaml_path, data)
    
    assert os.path.exists(yaml_path)
    with open(yaml_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
        assert loaded["ui"]["title"] == "Hello YAML"
