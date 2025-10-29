"""
Core library API for jupyter-remote-exec.

This module exposes a plain-Python interface usable from scripts, CLIs, tests,
or notebooks without relying on IPython magics. The optional IPython extension
(`jupyter_remote_exec_magic_wrapper.py`) is a thin wrapper over this API.
"""
from __future__ import annotations

from typing import Callable, Iterable, Optional, List, Dict, Any
import inspect

from config import get_remotes as cfg_get_remotes, materialize_remote
from http_client import create_kernel, JupyterHTTPError
from ws_client import execute_code_over_ws, JupyterWSError

# In-memory cache of active kernels, keyed by remote name.
# Each value: {
#   'host': str, 'port': int, 'https': bool, 'verify': bool|str|None,
#   'token': Optional[str], 'kernel_id': str
# }
_active_kernels: Dict[str, Dict[str, Any]] = {}


def get_remotes() -> List[str]:
    """Return the list of configured remote names from the configuration layer."""
    remotes = cfg_get_remotes()
    # Ensure we always return a list of strings
    return list(remotes)


def _ensure_kernel(remote_name: str) -> bool:
    """Ensure a remote kernel exists for the given remote name.

    Returns True on success, False on failure (and prints a short message).
    """
    if remote_name in _active_kernels:
        return True

    resolved = materialize_remote(remote_name)
    if not resolved:
        print(f"❌ Missing host/port for remote: {remote_name}")
        return False

    host = resolved['host']
    port = resolved['port']
    https = bool(resolved.get('https', False))
    verify = resolved.get('verify')
    token = resolved.get('token')

    try:
        kernel_id = create_kernel(host, port, token, https=https, verify=verify)
    except JupyterHTTPError as e:
        print(f"❌ Failed to create kernel for {remote_name}: {e}")
        return False

    _active_kernels[remote_name] = {
        'host': host,
        'port': port,
        'https': https,
        'verify': verify,
        'token': token,
        'kernel_id': kernel_id,
    }
    return True


def exec_code_on_remote(code: str, remotes: Optional[Iterable[str]] = None) -> str:
    """Execute arbitrary Python source code on one or more remotes.

    Args:
        code: Python source to run on the target remotes.
        remotes: None for all configured remotes; a remote name (str); or an
                 iterable of remote names.

    Returns:
        Concatenated stdout from all remotes in order.
    """
    if remotes is None:
        remote_list: List[str] = get_remotes()
    elif isinstance(remotes, str):
        remote_list = [remotes]
    else:
        remote_list = list(remotes)

    outputs: List[str] = []
    for remote_name in remote_list:
        if remote_name == 'local':
            # Execute locally as a convenience: create a minimal namespace.
            local_ns: Dict[str, Any] = {}
            try:
                exec(code, local_ns, local_ns)
            except Exception as e:
                outputs.append(f"❌ Local execution failed: {e}\n")
            continue

        if remote_name not in get_remotes():
            outputs.append(f"❌ Unknown remote: {remote_name}\n")
            continue

        if not _ensure_kernel(remote_name):
            # _ensure_kernel already printed a reason
            continue

        info = _active_kernels[remote_name]
        try:
            out = execute_code_over_ws(
                info['host'], info['port'], info['kernel_id'], info.get('token'), code,
                https=bool(info.get('https', False)), verify=info.get('verify')
            )
            outputs.append(out)
        except JupyterWSError as e:
            outputs.append(f"❌ Remote execution failed for {remote_name}: {e}\n")

    return ''.join(outputs)


def exec_on_remote(func: Callable, remotes: Optional[Iterable[str]] = None) -> str:
    """Execute a Python function on the specified remote(s).

    The function's source is sent to the remote and then invoked by name.
    """
    source = inspect.getsource(func)
    code = source + f"\n{func.__name__}()"
    return exec_code_on_remote(code, remotes)
