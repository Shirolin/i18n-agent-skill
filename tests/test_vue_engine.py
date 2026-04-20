from i18n_agent_skill.tools import TreeSitterScanner

VUE_SFC_CONTENT = """
<template>
  <div class="container">
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
import { ref } from 'vue'
const title = ref('来自 Setup 脚本的标题')
console.log(`调试信息: ${title.value}`)
</script>

<style scoped>
.container { color: red; }
</style>
"""


def test_vue_sfc_full_extraction():
    """验证 Vue SFC 的全量提取，包括模板文本、属性和脚本块"""
    scanner = TreeSitterScanner(VUE_SFC_CONTENT, ".vue")
    results = scanner.scan()

    # 提取所有文本内容
    texts = [r[0].strip() for r in results]
    line_nos = [r[1] for r in results]

    # 1. 验证模板文本提取
    assert "欢迎使用 Vue 国际化" in texts
    assert "这是一个测试段落。" in texts
    assert "提交" in texts

    # 2. 验证模板属性提取 (placeholder, title)
    assert "请输入用户名" in texts
    assert "点击提交" in texts

    # 3. 验证脚本块提取
    assert "来自普通脚本的消息" in texts
    assert "来自 Setup 脚本的标题" in texts
    assert "调试信息: {var}" in texts

    # 4. 验证行号精准度
    # "欢迎使用 Vue 国际化" 应该在第 4 行
    # Find its index
    idx = texts.index("欢迎使用 Vue 国际化")
    assert line_nos[idx] == 4

    # "来自 Setup 脚本的标题" 应该在第 23 行
    idx_setup = texts.index("来自 Setup 脚本的标题")
    assert line_nos[idx_setup] == 23


def test_vue_line_number_offset_stability():
    """验证脚本块解析时的行号偏移是否正确"""
    # 故意在顶部增加空行
    content = "\n\n" + VUE_SFC_CONTENT
    scanner = TreeSitterScanner(content, ".vue")
    results = scanner.scan()

    texts = [r[0].strip() for r in results]
    line_nos = [r[1] for r in results]

    # 原本在第 4 行的文本现在应该在第 6 行
    idx = texts.index("欢迎使用 Vue 国际化")
    assert line_nos[idx] == 6

    # Setup 脚本中的内容也应该顺延 (23 + 2 = 25)
    idx_setup = texts.index("来自 Setup 脚本的标题")
    assert line_nos[idx_setup] == 25
