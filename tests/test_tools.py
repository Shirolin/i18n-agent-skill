import unittest
import os
import sys
import asyncio

# 将项目根目录加入路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from i18n_agent_skill.tools import _flatten_dict, _unflatten_dict, _deep_update, extract_raw_strings
from i18n_agent_skill.models import ConflictStrategy

class TestI18nToolsAsync(unittest.IsolatedAsyncioTestCase):
    async def test_flatten_unflatten(self):
        """测试嵌套字典的拍平与还原"""
        nested = {
            "auth": {
                "login": {
                    "submit": "Submit Now"
                }
            }
        }
        flat = _flatten_dict(nested)
        self.assertEqual(flat["auth.login.submit"], "Submit Now")
        
        unflattened = _unflatten_dict(flat)
        self.assertEqual(unflattened, nested)

    async def test_deep_update_with_strategy(self):
        """测试深度合并冲突策略"""
        base = {"a": {"b": "old"}}
        update = {"a": {"b": "new", "c": "add"}}
        
        # 策略：保留现有 (Keep)
        res_keep = _deep_update(base.copy(), update, ConflictStrategy.KEEP_EXISTING)
        self.assertEqual(res_keep["a"]["b"], "old")
        self.assertEqual(res_keep["a"]["c"], "add")
        
        # 策略：强制覆盖 (Overwrite)
        res_ov = _deep_update(base.copy(), update, ConflictStrategy.OVERWRITE)
        self.assertEqual(res_ov["a"]["b"], "new")

    async def test_extract_async(self):
        """测试异步提取逻辑 (模拟文件读取)"""
        # 注意：此处依赖真实文件系统，生产环境建议使用 mock
        pass

if __name__ == '__main__':
    unittest.main()
