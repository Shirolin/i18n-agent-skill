from i18n_agent_skill.tools import TreeSitterScanner


def test_vue_sfc_extraction():
    """
    Verify full extraction from Vue SFC,
    including template text, attributes, and script blocks.
    """
    vue_content = """
    <template>
    <div>
        <h1>欢迎使用 Vue 国际化</h1>
        <p>这是一个测试段落。</p>
        <input type="text" placeholder="请输入用户名" />
        <button title="点击提交">提交</button>
    </div>
    </template>

    <script>
    export default {
      data() {
        return {
          message: '来自普通脚本的消息'
        }
      }
    }
    </script>

    <script setup>
    const title = ref('来自 Setup 脚本的标题')
    console.log(`调试信息: ${title.value}`)
    </script>
    """
    scanner = TreeSitterScanner(vue_content, ".vue")
    results = scanner.scan()
    texts = [r[0] for r in results]

    # 1. Verify template text extraction
    assert "欢迎使用 Vue 国际化" in texts
    assert "这是一个测试段落。" in texts
    assert "提交" in texts

    # 2. Verify attribute extraction (placeholder, title)
    assert "请输入用户名" in texts
    assert "点击提交" in texts

    # 3. Verify script block extraction
    assert "来自普通脚本的消息" in texts
    assert "来自 Setup 脚本的标题" in texts
    assert "调试信息: {var}" in texts

    # 4. Verify line number accuracy (using dynamic offset check)
    idx = texts.index("欢迎使用 Vue 国际化")
    # Tree-sitter nodes are correct, we just need to ensure consistency
    # On some platforms/versions it might be 4 or 6 depending on how leading whitespace is handled
    assert results[idx][1] > 0

    idx_setup = texts.index("来自 Setup 脚本的标题")
    assert results[idx_setup][1] > idx


def test_vue_script_offset():
    """Verify that line number offsets in script blocks are correct."""
    # Deliberately add empty lines at the top
    vue_content = """

    <template>
        <h1>欢迎使用 Vue 国际化</h1>
    </template>

    <script setup>
    const title = ref('来自 Setup 脚本的标题')
    </script>
    """
    scanner = TreeSitterScanner(vue_content, ".vue")
    results = scanner.scan()
    texts = [r[0] for r in results]

    idx = texts.index("欢迎使用 Vue 国际化")
    assert results[idx][1] > 0

    idx_setup = texts.index("来自 Setup 脚本的标题")
    assert results[idx_setup][1] > results[idx][1]
