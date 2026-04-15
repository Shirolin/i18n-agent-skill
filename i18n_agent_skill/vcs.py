import subprocess
import re
import os
from typing import Dict, Set

def get_git_hunks(workspace_root: str) -> Dict[str, Set[int]]:
    """
    解析 git diff -U0 的输出，提取每个变动文件的“变动行号集合”。
    用于实现 PR 级 Hunk 精准文案提取。
    """
    hunks: Dict[str, Set[int]] = {}
    current_file = ""
    
    try:
        # -U0 表示不包含上下文行，仅输出变动行
        result = subprocess.run(
            ["git", "diff", "-U0"], 
            cwd=workspace_root, 
            capture_output=True, 
            text=True, 
            encoding="utf-8",
            check=False
        )
        
        if result.returncode != 0:
            return {}

        for line in result.stdout.splitlines():
            # 匹配文件名
            if line.startswith("+++ b/"):
                current_file = line[6:]
                hunks[current_file] = set()
            # 匹配变动行区间: @@ -1,1 +1,1 @@ -> 提取第 2 组 (目标文件行)
            elif line.startswith("@@ ") and current_file:
                match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    start_line = int(match.group(1))
                    line_count = int(match.group(2)) if match.group(2) else 1
                    
                    # 记录变动的行区间（包含前后 1 行缓冲）
                    for i in range(start_line - 1, start_line + line_count + 1):
                        hunks[current_file].add(i)
                        
    except Exception:
        pass
    return hunks
