"""
Core library API for jupyter-remote-exec.

This module exposes a plain-Python interface usable from scripts, CLIs, tests,
or notebooks without relying on IPython magics. The optional IPython extension
(`jupyter_remote_exec_magic_wrapper.py`) is a thin wrapper over this API.
"""
from __future__ import annotations

from typing import Iterable, Optional, List, Dict, Any, Callable, TextIO
import sys
import inspect

from .config import get_remotes as cfg_get_remotes, materialize_remote
from .http_client import create_kernel, JupyterHTTPError
from .ws_client import execute_code_over_ws, JupyterWSError

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


def _resolve_remote_list(remotes: Optional[Iterable[str]]) -> List[str]:
    """Normalize the `remotes` argument to a list of names.

    None -> all configured remotes; str -> [str]; iterable -> list(iterable)
    """
    if remotes is None:
        return list(get_remotes())
    if isinstance(remotes, str):
        return [remotes]
    return list(remotes)


def _exec_on_remotes(code: str, remotes: Optional[Iterable[str]] = None, file=sys.stdout, with_header: bool = False):
    """Execute code on target remotes and write output to file.

    Args:
        code: Python code to execute
        remotes: Target remotes
        file: Output stream for writing output (default: sys.stdout)
        with_header: If True, print separator header before each remote execution
    """
    remote_list = _resolve_remote_list(remotes)

    for remote_name in remote_list:
        # Print header before execution if requested
        if with_header:
            header = f"\n----- [ {remote_name} ] " + "-" * 40
            file.write(header + "\n")
            file.flush()

        if remote_name not in get_remotes():
            error_msg = f"❌ Unknown remote: {remote_name}\n"
            file.write(error_msg)
            file.flush()
            continue

        if not _ensure_kernel(remote_name):
            # _ensure_kernel already printed a reason
            continue

        info = _active_kernels[remote_name]
        try:
            execute_code_over_ws(
                info['host'], info['port'], info['kernel_id'], info.get('token'), code,
                https=bool(info.get('https', False)), verify=info.get('verify'),
                file=file
            )
        except JupyterWSError as e:
            error_msg = f"❌ Remote execution failed for {remote_name}: {e}\n"
            file.write(error_msg)
            file.flush()


def exec_on_remote(func: Callable, remotes: Optional[Iterable[str]] = None, *, separators: Optional[bool] = None) -> None:
    """Execute a Python function on the specified remote(s).

    Prints the remote stdout naturally (no quotes, real newlines) in real-time and returns None.
    The function's source is sent to the remote and then invoked by name.

    Args:
        func: Callable to send and execute remotely.
        remotes: Target remote(s). None means all configured.
        separators: If True, print a header separator per remote. If False, no
            separators. If None (default), automatically add separators when
            targeting multiple remotes.
    """
    source = inspect.getsource(func)
    code = source + f"\n{func.__name__}()"

    remote_list = _resolve_remote_list(remotes)
    auto_sep = (separators if separators is not None else len(remote_list) > 1)

    _exec_on_remotes(code, remote_list, with_header=auto_sep)


def shell_on_remote(code: str, remotes: Optional[Iterable[str]] = None, *, separators: Optional[bool] = None) -> None:
    """Execute Python code (single-line or multi-line) on the specified remote(s).

    Args:
        code: Python source to execute remotely. Can be a single line or a block.
        remotes: None for all configured remotes; a single remote name; or an
                 iterable of remote names.
        separators: If True, print a header separator per remote. If False, no
            separators. If None (default), automatically add separators when
            targeting multiple remotes.

    Behavior:
        - Sends the code as-is to the remote kernel(s) and executes it.
        - Prints stdout in natural form (no quotes) in real-time and returns None.
    """
    if not isinstance(code, str):
        raise TypeError("code must be a string containing Python source code")

    remote_list = _resolve_remote_list(remotes)
    auto_sep = (separators if separators is not None else len(remote_list) > 1)

    _exec_on_remotes(code, remote_list, with_header=auto_sep)