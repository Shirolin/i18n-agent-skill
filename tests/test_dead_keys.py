import json
import os
import shutil
import tempfile

import pytest

from i18n_agent_skill import tools


@pytest.fixture
def mock_project(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", tmp_dir)

    # 1. Create locales
    locales_dir = os.path.join(tmp_dir, "locales")
    os.makedirs(locales_dir)
    en_content = {
        "common": {"welcome": "Welcome", "unused_key": "Should be dead"},
        "auth": {"login": "Login", "logout": "Logout"},
        "abandoned": "Totally unused",
    }
    with open(os.path.join(locales_dir, "en.json"), "w") as f:
        json.dump(en_content, f)

    # 2. Create source code
    src_dir = os.path.join(tmp_dir, "src")
    os.makedirs(src_dir)
    code_content = """
    import React from 'react';
    const App = () => {
        const { t } = useTranslation();
        return (
            <div>
                <h1>{t('common.welcome')}</h1>
                <button>{$t('auth.login')}</button>
                <span>{i18n.t('auth.logout')}</span>
            </div>
        );
    }
    """
    with open(os.path.join(src_dir, "App.tsx"), "w") as f:
        f.write(code_content)

    # 3. Create config
    config = {"locales_dir": "locales", "source_dirs": ["src"]}
    with open(os.path.join(tmp_dir, ".i18n-skill.json"), "w") as f:
        json.dump(config, f)

    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.mark.asyncio
async def test_get_dead_keys(mock_project):
    # Dead keys should be:
    # 1. common.unused_key
    # 2. abandoned
    dead_keys = await tools.get_dead_keys("en")

    assert "common.unused_key" in dead_keys
    assert "abandoned" in dead_keys
    assert "common.welcome" not in dead_keys
    assert "auth.login" not in dead_keys
    assert len(dead_keys) == 2
