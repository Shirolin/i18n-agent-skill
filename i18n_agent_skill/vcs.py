import subprocess
import re
import os
from typing import Dict, List, Set

def get_git_hunks(workspace_root: str) -> Dict[str, Set[int]]:
    """
    皇冠级特性：PR 级 Hunk 精准定位。
    解析 git diff -U0 的输出，提取每个变动文件的“变动行号集合”。
    """
    hunks = {}
    try:
        # -U0 意味着不显示上下文行，只显示发生变动的行
        result = subprocess.run(
            ["git", "diff", "-U0", "--no-color"],
            capture_output=True, text=True, check=True, cwd=workspace_root
        )
        
        current_file = None
        # 正则匹配 Git diff 的 hunk 头部，例如: @@ -10,2 +15,3 @@
        hunk_header_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
        
        for line in result.stdout.splitlines():
            if line.startswith('---') or line.startswith('+++'):
                if line.startswith('+++ b/'):
                    current_file = line[6:]
                    hunks[current_file] = set()
                continue
            
            if current_file:
                match = hunk_header_re.match(line)
                if match:
                    start_line = int(match.group(1))
                    line_count = int(match.group(2)) if match.group(2) else 1
                    # 记录变动的行区间（包含前后 1 行缓冲）
                    for i in range(start_line - 1, start_line + line_count + 1):
                        hunks[current_file].add(i)
                        
    except Exception:
        pass
    return hunks
