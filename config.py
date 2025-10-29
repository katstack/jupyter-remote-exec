"""
Configuration utilities for jupyter-remote-exec.

Supports multiple sources with the following precedence (highest first):
1) Programmatic runtime configuration via set_config()
2) Project/User config files (pyproject.toml [tool.jupyter_remote_exec] or jupyter_remote_exec.json)
3) Environment variables (JRE_*)
4) In-file legacy defaults (fallbacks passed by callers if nothing else found)

Schema (conceptual):
{
  "shared_token": "...",                 # optional
  "remotes": {
      "us-east": {
          "host": "localhost",
          "port": 8888,
          "https": false,                 # optional; default False
          "verify": null,                 # optional; True|False|str(path)
          "token": "..."                 # optional per-remote token
      },
      ...
  }
}

Environment variables (optional):
- JRE_SHARED_TOKEN
- JRE_DEFAULT_HTTPS ("true"/"false")
- JRE_DEFAULT_VERIFY ("true"/"false"/path)
- Per-remote overrides (REMOTE name uppercased, non-alnum replaced with underscore):
  - JRE_REMOTE_<NAME>_HOST
  - JRE_REMOTE_<NAME>_PORT
  - JRE_REMOTE_<NAME>_HTTPS
  - JRE_REMOTE_<NAME>_VERIFY
  - JRE_REMOTE_<NAME>_TOKEN

Programmatic override:
- set_config(dict) to replace current configuration at runtime.

Utilities:
- get_config()
- get_remotes() -> List[str]
- get_remote(name) -> dict | None
- resolve_token_for(remote_name) -> Optional[str]
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List
import json
import os

# Try to support TOML via stdlib (Python 3.11+); fall back to optional tomli if present.
try:
    import tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore
    try:
        import tomli as _tomli  # type: ignore
    except Exception:
        _tomli = None  # type: ignore

# In-memory programmatic config (highest precedence)
_RUNTIME_CONFIG: Optional[Dict[str, Any]] = None


def _to_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    v = val.strip().lower()
    if v in ("1", "true", "yes", "y", "on"): return True
    if v in ("0", "false", "no", "n", "off"): return False
    return None


def set_config(cfg: Dict[str, Any]) -> None:
    """Set configuration programmatically for the current process.

    Passing a dict replaces any previously set runtime config.
    """
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = cfg


def get_config() -> Dict[str, Any]:
    """Load configuration from all supported sources honoring precedence.

    Returns a dict adhering to the schema described above. Missing keys are simply
    absent; callers should apply sensible defaults.
    """
    # 1) Programmatic override
    if _RUNTIME_CONFIG is not None:
        return _RUNTIME_CONFIG

    # 2) File-based configuration (pyproject.toml or jupyter_remote_exec.json)
    file_cfg: Dict[str, Any] = {}
    # pyproject.toml
    pyproject_path = os.path.join(os.getcwd(), "pyproject.toml")
    if tomllib and os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            section = data.get("tool", {}).get("jupyter_remote_exec")
            if isinstance(section, dict):
                file_cfg = section
        except Exception:
            # ignore malformed files to keep runtime simple
            pass
    elif not tomllib and 'PYPROJECT_TOML' in os.environ:
        # optional: explicit path via env, try tomli if available
        p = os.environ['PYPROJECT_TOML']
        parser = tomllib or _tomli
        if parser and os.path.exists(p):
            try:
                mode = "rb" if parser is tomllib else "rb"
                with open(p, mode) as f:  # type: ignore
                    data = parser.load(f)  # type: ignore
                section = data.get("tool", {}).get("jupyter_remote_exec")
                if isinstance(section, dict):
                    file_cfg = section
            except Exception:
                pass

    # jupyter_remote_exec.json (simple JSON alternative)
    if not file_cfg:
        json_path = os.path.join(os.getcwd(), "jupyter_remote_exec.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    file_cfg = json.load(f)
            except Exception:
                file_cfg = {}

    # 3) Environment variables
    env_cfg: Dict[str, Any] = {}
    shared_token = os.environ.get("JRE_SHARED_TOKEN")
    if shared_token:
        env_cfg["shared_token"] = shared_token

    default_https = _to_bool(os.environ.get("JRE_DEFAULT_HTTPS"))
    default_verify_env = os.environ.get("JRE_DEFAULT_VERIFY")
    default_verify: Optional[bool | str]
    if default_verify_env is None:
        default_verify = None
    else:
        b = _to_bool(default_verify_env)
        default_verify = b if b is not None else default_verify_env  # a path string

    # Collect per-remote env overrides by scanning env keys
    remotes_env: Dict[str, Dict[str, Any]] = {}
    prefix = "JRE_REMOTE_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        try:
            rest = key[len(prefix):]
            name, field = rest.split("_", 1)
        except ValueError:
            continue
        rname = name.lower()
        rem = remotes_env.setdefault(rname, {})
        f = field.lower()
        if f == "host":
            rem["host"] = value
        elif f == "port":
            try:
                rem["port"] = int(value)
            except ValueError:
                pass
        elif f == "https":
            b = _to_bool(value)
            if b is not None:
                rem["https"] = b
        elif f == "verify":
            b = _to_bool(value)
            rem["verify"] = b if b is not None else value  # path string
        elif f == "token":
            rem["token"] = value

    if remotes_env:
        env_cfg["remotes"] = remotes_env
    if default_https is not None or default_verify is not None:
        env_cfg.setdefault("defaults", {})
        if default_https is not None:
            env_cfg["defaults"]["https"] = default_https
        if default_verify is not None:
            env_cfg["defaults"]["verify"] = default_verify

    # Merge: file_cfg <- env_cfg (env wins)
    merged: Dict[str, Any] = {}
    # start with file config
    for k, v in file_cfg.items():
        merged[k] = v
    # overlay env
    for k, v in env_cfg.items():
        if k != "remotes":
            merged[k] = v
    # deep-merge remotes
    remotes: Dict[str, Any] = {}
    if isinstance(file_cfg.get("remotes"), dict):
        remotes.update(file_cfg["remotes"])  # type: ignore[arg-type]
    if isinstance(env_cfg.get("remotes"), dict):
        for rname, rconf in env_cfg["remotes"].items():  # type: ignore[assignment]
            base = remotes.get(rname, {})
            base.update(rconf)
            remotes[rname] = base
    if remotes:
        merged["remotes"] = remotes

    return merged


def get_remotes() -> List[str]:
    cfg = get_config()
    remotes = cfg.get("remotes")
    if isinstance(remotes, dict):
        return list(remotes.keys())
    return []


def get_remote(name: str) -> Optional[Dict[str, Any]]:
    cfg = get_config()
    remotes = cfg.get("remotes")
    if isinstance(remotes, dict):
        rc = remotes.get(name)
        if isinstance(rc, dict):
            return rc
    return None


def resolve_token_for(remote_name: str, legacy_shared_token: Optional[str] = None) -> Optional[str]:
    """Return token by precedence: per-remote token -> shared_token -> legacy_shared_token -> None"""
    cfg = get_config()
    per = None
    r = get_remote(remote_name)
    if r:
        per = r.get("token")
    if per:
        return per
    shared = cfg.get("shared_token")
    if shared:
        return shared
    return legacy_shared_token


def materialize_remote(remote_name: str,
                       legacy_defaults: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Return a complete remote dict applying defaults and precedence.

    legacy_defaults can include keys: host, port, https, verify, token
    """
    # Base from config
    rc = get_remote(remote_name) or {}

    md: Dict[str, Any] = {}
    # Host/port required
    if "host" in rc:
        md["host"] = rc["host"]
    elif legacy_defaults and "host" in legacy_defaults:
        md["host"] = legacy_defaults["host"]

    if "port" in rc:
        md["port"] = rc["port"]
    elif legacy_defaults and "port" in legacy_defaults:
        md["port"] = legacy_defaults["port"]

    # HTTPS and verify
    defaults = get_config().get("defaults", {}) if isinstance(get_config().get("defaults"), dict) else {}
    md["https"] = rc.get("https", (legacy_defaults or {}).get("https", defaults.get("https", False)))
    md["verify"] = rc.get("verify", (legacy_defaults or {}).get("verify", defaults.get("verify")))

    # Token resolved separately
    token = rc.get("token")
    if token is None:
        # use shared token (from config) or legacy provided SHARED_TOKEN
        token = get_config().get("shared_token", (legacy_defaults or {}).get("token"))
    md["token"] = token

    # Return only if host/port are available
    if "host" in md and "port" in md:
        return md
    return None
