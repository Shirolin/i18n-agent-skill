import re
import subprocess


def get_git_hunks(workspace_root: str) -> dict[str, set[int]]:
    """
    Parse the output of 'git diff -U0' and extract the set of changed line numbers for each file.
    Used for precise string extraction at the PR/Hunk level.
    """
    hunks: dict[str, set[int]] = {}
    current_file = ""

    try:
        # -U0 means no context lines, only changed lines are output
        result = subprocess.run(
            ["git", "diff", "-U0"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        if result.returncode != 0:
            return {}

        for line in result.stdout.splitlines():
            # Match filename
            if line.startswith("+++ b/"):
                current_file = line[6:]
                hunks[current_file] = set()
            # Match line range: @@ -1,1 +1,1 @@ -> Extract 2nd group (target file lines)
            elif line.startswith("@@ ") and current_file:
                match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    start_line = int(match.group(1))
                    line_count = int(match.group(2)) if match.group(2) else 1

                    # Record changed line range (including 1-line buffer)
                    for i in range(start_line - 1, start_line + line_count + 1):
                        hunks[current_file].add(i)

    except Exception:
        pass
    return hunks
