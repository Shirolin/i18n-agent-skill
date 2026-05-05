import re
import subprocess


def get_vcs_status(workspace_root: str) -> dict | None:
    """
    Get detailed Git repository status.
    Returns: {branch, commit_hash, uncommitted_changes_count}
    """
    try:
        # 1. Get branch name
        branch_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace_root, capture_output=True, text=True, check=False
        )
        if branch_res.returncode != 0:
            return None
        
        # 2. Get short commit hash
        hash_res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=workspace_root, capture_output=True, text=True, check=False
        )

        # 3. Get count of uncommitted changes
        diff_res = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=workspace_root, capture_output=True, text=True, check=False
        )
        changes = diff_res.stdout.strip().split("\n") if diff_res.stdout.strip() else []

        return {
            "branch": branch_res.stdout.strip(),
            "commit_hash": hash_res.stdout.strip() if hash_res.returncode == 0 else "unknown",
            "uncommitted_changes_count": len(changes),
            "is_dirty": len(changes) > 0
        }
    except Exception:
        return None


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
