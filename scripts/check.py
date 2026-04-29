#!/usr/bin/env python3
import subprocess
import sys


def run_command(command, label):
    print(f">>> Running {label}...")
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"OK: {label} passed!")
        return True
    except subprocess.CalledProcessError:
        print(f"FAIL: {label} failed!")
        return False


def main():
    success = True

    # 1. Ruff Format
    if not run_command("ruff format .", "Ruff Format"):
        success = False

    # 2. Ruff Lint
    if not run_command("ruff check . --fix", "Ruff Lint"):
        success = False

    # 3. Mypy Type Check
    mypy_cmd = (
        "mypy i18n_agent_skill --ignore-missing-imports "
        "--disable-error-code=union-attr --disable-error-code=assignment"
    )
    if not run_command(mypy_cmd, "Mypy Type Check"):
        success = False

    if not success:
        print("\nERROR: Please fix the issues above before committing.")
        sys.exit(1)

    print("\nAll checks passed! Ready to commit.")


if __name__ == "__main__":
    main()
