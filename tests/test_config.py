"""Tests for configuration utilities."""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict
import pytest

from jupyter_remote_exec.config import (
    set_config,
    get_config,
    get_remotes,
    get_remote,
    resolve_token_for,
    materialize_remote,
    _to_bool,
    _RUNTIME_CONFIG,
)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all JRE environment variables."""
    for key in list(os.environ.keys()):
        if key.startswith("JRE_"):
            monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def clean_runtime():
    """Clean runtime configuration before and after each test."""
    import jupyter_remote_exec.config as config_module
    config_module._RUNTIME_CONFIG = None
    yield
    config_module._RUNTIME_CONFIG = None


@pytest.fixture
def temp_project_dir(monkeypatch, clean_env, clean_runtime):
    """Create a temporary directory and set it as the current working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        yield Path(tmpdir)


class TestToBool:
    """Test the _to_bool utility function."""

    def test_true_values(self):
        assert _to_bool("true") is True
        assert _to_bool("TRUE") is True
        assert _to_bool("1") is True
        assert _to_bool("yes") is True
        assert _to_bool("y") is True
        assert _to_bool("on") is True

    def test_false_values(self):
        assert _to_bool("false") is False
        assert _to_bool("FALSE") is False
        assert _to_bool("0") is False
        assert _to_bool("no") is False
        assert _to_bool("n") is False
        assert _to_bool("off") is False

    def test_none_value(self):
        assert _to_bool(None) is None

    def test_invalid_values(self):
        assert _to_bool("invalid") is None
        assert _to_bool("maybe") is None


class TestSetConfig:
    """Test programmatic configuration."""

    def test_set_config(self, clean_runtime):
        cfg = {"shared_token": "test_token", "remotes": {"local": {"host": "localhost", "port": 8888}}}
        set_config(cfg)
        assert get_config() == cfg

    def test_set_config_override(self, clean_runtime):
        cfg1 = {"shared_token": "token1"}
        cfg2 = {"shared_token": "token2"}
        set_config(cfg1)
        assert get_config()["shared_token"] == "token1"
        set_config(cfg2)
        assert get_config()["shared_token"] == "token2"


class TestGetConfigToml:
    """Test configuration loading from config.toml."""

    def test_load_from_config_toml(self, temp_project_dir):
        config = temp_project_dir / "config.toml"
        config.write_text("""
shared_token = "file_token"

[remotes.dev]
host = "dev.example.com"
port = 8888
https = true

[remotes.prod]
host = "prod.example.com"
port = 8888
token = "prod_token"
""")
        cfg = get_config()
        assert cfg["shared_token"] == "file_token"
        assert cfg["remotes"]["dev"]["host"] == "dev.example.com"
        assert cfg["remotes"]["dev"]["port"] == 8888
        assert cfg["remotes"]["dev"]["https"] is True
        assert cfg["remotes"]["prod"]["token"] == "prod_token"

    def test_missing_config_toml(self, temp_project_dir):
        cfg = get_config()
        assert cfg == {}

    def test_malformed_config_toml(self, temp_project_dir):
        config = temp_project_dir / "config.toml"
        config.write_text("this is not valid toml [[[]")
        cfg = get_config()
        assert cfg == {}


class TestGetConfigEnvironment:
    """Test configuration loading from environment variables."""

    def test_shared_token_from_env(self, clean_env, clean_runtime, monkeypatch):
        monkeypatch.setenv("JRE_SHARED_TOKEN", "env_token")
        cfg = get_config()
        assert cfg["shared_token"] == "env_token"

    def test_default_https_from_env(self, clean_env, clean_runtime, monkeypatch):
        monkeypatch.setenv("JRE_DEFAULT_HTTPS", "true")
        cfg = get_config()
        assert cfg["defaults"]["https"] is True

    def test_default_verify_bool_from_env(self, clean_env, clean_runtime, monkeypatch):
        monkeypatch.setenv("JRE_DEFAULT_VERIFY", "false")
        cfg = get_config()
        assert cfg["defaults"]["verify"] is False

    def test_default_verify_path_from_env(self, clean_env, clean_runtime, monkeypatch):
        monkeypatch.setenv("JRE_DEFAULT_VERIFY", "/path/to/cert.pem")
        cfg = get_config()
        assert cfg["defaults"]["verify"] == "/path/to/cert.pem"

    def test_remote_from_env(self, clean_env, clean_runtime, monkeypatch):
        monkeypatch.setenv("JRE_REMOTE_LOCAL_HOST", "localhost")
        monkeypatch.setenv("JRE_REMOTE_LOCAL_PORT", "9999")
        monkeypatch.setenv("JRE_REMOTE_LOCAL_HTTPS", "true")
        monkeypatch.setenv("JRE_REMOTE_LOCAL_TOKEN", "local_token")
        cfg = get_config()
        assert cfg["remotes"]["local"]["host"] == "localhost"
        assert cfg["remotes"]["local"]["port"] == 9999
        assert cfg["remotes"]["local"]["https"] is True
        assert cfg["remotes"]["local"]["token"] == "local_token"

    def test_remote_verify_path_from_env(self, clean_env, clean_runtime, monkeypatch):
        monkeypatch.setenv("JRE_REMOTE_DEV_HOST", "dev.local")
        monkeypatch.setenv("JRE_REMOTE_DEV_PORT", "8888")
        monkeypatch.setenv("JRE_REMOTE_DEV_VERIFY", "/custom/cert.pem")
        cfg = get_config()
        assert cfg["remotes"]["dev"]["verify"] == "/custom/cert.pem"


class TestGetConfigPrecedence:
    """Test configuration precedence: runtime > env > file."""

    def test_runtime_overrides_file(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""
shared_token = "file_token"
""")
        set_config({"shared_token": "runtime_token"})
        cfg = get_config()
        assert cfg["shared_token"] == "runtime_token"

    def test_env_overrides_file(self, temp_project_dir, clean_runtime, monkeypatch):
        config = temp_project_dir / "config.toml"
        config.write_text("""
shared_token = "file_token"

[remotes.local]
host = "file.host"
port = 8888
""")
        monkeypatch.setenv("JRE_SHARED_TOKEN", "env_token")
        monkeypatch.setenv("JRE_REMOTE_LOCAL_HOST", "env.host")
        cfg = get_config()
        assert cfg["shared_token"] == "env_token"
        assert cfg["remotes"]["local"]["host"] == "env.host"
        assert cfg["remotes"]["local"]["port"] == 8888  # not overridden

    def test_runtime_highest_precedence(self, temp_project_dir, clean_runtime, monkeypatch):
        config = temp_project_dir / "config.toml"
        config.write_text("""
shared_token = "file_token"
""")
        monkeypatch.setenv("JRE_SHARED_TOKEN", "env_token")
        set_config({"shared_token": "runtime_token"})
        cfg = get_config()
        assert cfg["shared_token"] == "runtime_token"


class TestGetRemotes:
    """Test get_remotes function."""

    def test_get_remotes_empty(self, clean_env, clean_runtime):
        assert get_remotes() == []

    def test_get_remotes_from_config(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""
[remotes.dev]
host = "dev.example.com"
port = 8888

[remotes.prod]
host = "prod.example.com"
port = 8888
""")
        remotes = get_remotes()
        assert set(remotes) == {"dev", "prod"}


class TestGetRemote:
    """Test get_remote function."""

    def test_get_remote_exists(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""
[remotes.dev]
host = "dev.example.com"
port = 8888
https = true
""")
        remote = get_remote("dev")
        assert remote is not None
        assert remote["host"] == "dev.example.com"
        assert remote["port"] == 8888
        assert remote["https"] is True

    def test_get_remote_not_exists(self, clean_env, clean_runtime):
        assert get_remote("nonexistent") is None


class TestResolveTokenFor:
    """Test resolve_token_for function."""

    def test_per_remote_token_priority(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""

shared_token = "shared"

[remotes.dev]
host = "dev.example.com"
port = 8888
token = "per_remote"
""")
        token = resolve_token_for("dev")
        assert token == "per_remote"

    def test_shared_token_fallback(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""

shared_token = "shared"

[remotes.dev]
host = "dev.example.com"
port = 8888
""")
        token = resolve_token_for("dev")
        assert token == "shared"

    def test_legacy_token_fallback(self, clean_env, clean_runtime):
        token = resolve_token_for("dev", legacy_shared_token="legacy")
        assert token == "legacy"

    def test_no_token(self, clean_env, clean_runtime):
        token = resolve_token_for("dev")
        assert token is None


class TestMaterializeRemote:
    """Test materialize_remote function."""

    def test_materialize_complete_remote(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""

shared_token = "shared_token"

[remotes.dev]
host = "dev.example.com"
port = 8888
https = true
verify = false
token = "per_remote_token"
""")
        remote = materialize_remote("dev")
        assert remote is not None
        assert remote["host"] == "dev.example.com"
        assert remote["port"] == 8888
        assert remote["https"] is True
        assert remote["verify"] is False
        assert remote["token"] == "per_remote_token"

    def test_materialize_with_defaults(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""
[remotes.dev]
host = "dev.example.com"
port = 8888
""")
        remote = materialize_remote("dev")
        assert remote is not None
        assert remote["https"] is False  # default
        assert remote["verify"] is None  # default

    def test_materialize_with_legacy_defaults(self, clean_env, clean_runtime):
        legacy = {
            "host": "legacy.host",
            "port": 9999,
            "https": True,
            "verify": "/path/to/cert",
            "token": "legacy_token"
        }
        remote = materialize_remote("unknown", legacy_defaults=legacy)
        assert remote is not None
        assert remote["host"] == "legacy.host"
        assert remote["port"] == 9999
        assert remote["https"] is True
        assert remote["verify"] == "/path/to/cert"
        assert remote["token"] == "legacy_token"

    def test_materialize_config_overrides_legacy(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""
[remotes.dev]
host = "config.host"
port = 7777
""")
        legacy = {"host": "legacy.host", "port": 9999}
        remote = materialize_remote("dev", legacy_defaults=legacy)
        assert remote is not None
        assert remote["host"] == "config.host"
        assert remote["port"] == 7777

    def test_materialize_missing_host_port(self, clean_env, clean_runtime):
        remote = materialize_remote("nonexistent")
        assert remote is None

    def test_materialize_with_global_defaults(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""
[defaults]
https = true
verify = "/global/cert.pem"

[remotes.dev]
host = "dev.example.com"
port = 8888
""")
        remote = materialize_remote("dev")
        assert remote is not None
        assert remote["https"] is True
        assert remote["verify"] == "/global/cert.pem"

    def test_materialize_remote_overrides_global_defaults(self, temp_project_dir, clean_runtime):
        config = temp_project_dir / "config.toml"
        config.write_text("""
[defaults]
https = true
verify = true

[remotes.dev]
host = "dev.example.com"
port = 8888
https = false
verify = "/remote/cert.pem"
""")
        remote = materialize_remote("dev")
        assert remote is not None
        assert remote["https"] is False
        assert remote["verify"] == "/remote/cert.pem"
