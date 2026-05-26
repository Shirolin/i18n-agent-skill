import importlib.util
import subprocess
import sys
from pathlib import Path


def load_installer():
    installer_path = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
    spec = importlib.util.spec_from_file_location("i18n_skill_installer", installer_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_proxy_rebuilds_missing_or_broken_venv_python(tmp_path, monkeypatch):
    installer = load_installer()
    project_root = tmp_path / "project"
    skill_root = project_root / ".agents" / "skills" / "i18n-agent-skill"
    skill_root.mkdir(parents=True)

    monkeypatch.setattr(installer, "SKILL_ROOT", skill_root)
    monkeypatch.setattr(sys, "platform", "win32")

    installer.generate_command_proxy()

    proxy = project_root / "i18n.ps1"
    content = proxy.read_text(encoding="utf-8")

    assert "$VenvPython" in content
    assert "Test-Path" in content
    assert "scripts\\install.py" in content
    assert "-m i18n_agent_skill" in content
    assert "Test-I18nRuntime" in content
    assert "import i18n_agent_skill" in content


def test_find_python_prefers_current_interpreter(monkeypatch):
    installer = load_installer()

    def fail_if_path_python_is_used(*_args, **_kwargs):
        raise AssertionError("PATH Python should not be probed before sys.executable")

    monkeypatch.setattr(installer.subprocess, "run", fail_if_path_python_is_used)

    assert installer.find_python() == sys.executable


def test_setup_venv_bootstraps_pip_when_missing(tmp_path, monkeypatch):
    installer = load_installer()
    skill_root = tmp_path / "skill"
    venv_python = skill_root / ".venv" / "Scripts" / "python.exe"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(installer, "SKILL_ROOT", skill_root)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(installer, "pre_flight_check", lambda: None)
    monkeypatch.setattr(installer, "find_python", lambda: "python")

    calls = []
    pip_failed = {"value": False}

    def fake_run(cmd, check=False, **kwargs):
        calls.append(cmd)
        cmd_list = list(cmd)

        if cmd_list[:3] == [str(venv_python), "-m", "pip"] and not pip_failed["value"]:
            pip_failed["value"] = True
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd_list)

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    installer.setup_venv()

    assert [str(venv_python), "-m", "ensurepip", "--upgrade"] in calls
