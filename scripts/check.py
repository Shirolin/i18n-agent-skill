import os
import subprocess
import sys


def run(cmd, name):
    print(f"\n>>> Running {name}...")
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"OK: {name} passed!")
        return True
    except subprocess.CalledProcessError:
        print(f"FAIL: {name} failed!")
        return False


def main():
    # 确保在项目根目录
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    success = True

    # 1. Format (like Prettier)
    if not run("ruff format .", "Ruff Format"):
        success = False

    # 2. Lint (like ESLint)
    if not run("ruff check . --fix", "Ruff Lint"):
        success = False

    # 3. Type Check (like TSC)
    if not run("mypy .", "Mypy Type Check"):
        success = False

    if success:
        print("\nAll checks passed! Ready to commit.")
    else:
        print("\nERROR: Please fix the issues above before committing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
