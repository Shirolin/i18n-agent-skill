import pytest
import os
import json
from i18n_agent_skill import tools
from i18n_agent_skill.models import PrivacyLevel

@pytest.mark.asyncio
async def test_vue_sfc_region_recursion(tmp_path):
    """验证 Vue SFC 深度解析：template 的 HTML 与 script setup 的 JS 均能提取，排除 style。"""
    vue_content = """
    <template>
      <button title="点击提交">Submit</button>
    </template>
    <script setup>
    const msg = "逻辑中文";
    </script>
    <style>
    .btn { content: "ignore me"; }
    </style>
    """
    f = tmp_path / "App.vue"
    f.write_text(vue_content, encoding="utf-8")
    
    # 模拟 WORKSPACE_ROOT 以通过沙箱校验
    tools.WORKSPACE_ROOT = str(tmp_path)
    
    output = await tools.extract_raw_strings("App.vue")
    if output.error and output.error.error_code == "DEP_ERR":
        pytest.skip("Environment does not support Tree-sitter, skipping AST check.")
        
    texts = [r.text for r in output.results]
    assert "点击提交" in texts
    assert "Submit" in texts
    assert "逻辑中文" in texts
    assert "ignore me" not in texts

@pytest.mark.asyncio
async def test_jsx_text_node_capture(tmp_path):
    """验证 JSX 无引号文本节点捕获。"""
    tsx_content = """
    export const Comp = () => <div>保存修改</div>;
    """
    f = tmp_path / "Comp.tsx"
    f.write_text(tsx_content, encoding="utf-8")
    
    tools.WORKSPACE_ROOT = str(tmp_path)
    output = await tools.extract_raw_strings("Comp.tsx")
    if output.error and output.error.error_code == "DEP_ERR":
        pytest.skip("AST engine missing")
        
    texts = [r.text for r in output.results]
    assert "保存修改" in texts

@pytest.mark.asyncio
async def test_multilingual_召回率(tmp_path):
    """验证对日语、德语等非 ASCII 自然语言的 100% 召回。"""
    code = """
    const labels = {
      ja: "キャンセル",
      de: "Bestätigen"
    };
    """
    f = tmp_path / "global.js"
    f.write_text(code, encoding="utf-8")
    
    tools.WORKSPACE_ROOT = str(tmp_path)
    output = await tools.extract_raw_strings("global.js")
    if output.error and output.error.error_code == "DEP_ERR":
        pytest.skip("AST engine missing")
        
    texts = [r.text for r in output.results]
    assert "キャンセル" in texts
    assert "Bestätigen" in texts
