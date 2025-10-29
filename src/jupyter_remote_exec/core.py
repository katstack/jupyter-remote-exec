"""
Core library API for jupyter-remote-exec.

This module exposes a plain-Python interface usable from scripts, CLIs, tests,
or notebooks without relying on IPython magics. The optional IPython extension
(`jupyter_remote_exec_magic_wrapper.py`) is a thin wrapper over this API.
"""
from __future__ import annotations

from typing import Iterable, Optional, List, Dict, Any, Callable
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


def _iter_remote_outputs(code: str, remotes: Optional[Iterable[str]] = None):
    """Yield (remote_name, output_text) for each target remote/local.

    This mirrors `_exec_code_on_remote` logic but keeps outputs per remote.
    """
    remote_list = _resolve_remote_list(remotes)

    for remote_name in remote_list:
        if remote_name == 'local':
            local_ns: Dict[str, Any] = {}
            try:
                exec(code, local_ns, local_ns)
            except Exception as e:
                yield remote_name, f"❌ Local execution failed: {e}\n"
            else:
                # Local execution prints directly; no captured stdout here.
                yield remote_name, ''
            continue

        if remote_name not in get_remotes():
            yield remote_name, f"❌ Unknown remote: {remote_name}\n"
            continue

        if not _ensure_kernel(remote_name):
            # _ensure_kernel already printed a reason; emit empty output for consistency
            yield remote_name, ''
            continue

        info = _active_kernels[remote_name]
        try:
            out = execute_code_over_ws(
                info['host'], info['port'], info['kernel_id'], info.get('token'), code,
                https=bool(info.get('https', False)), verify=info.get('verify')
            )
            yield remote_name, out
        except JupyterWSError as e:
            yield remote_name, f"❌ Remote execution failed for {remote_name}: {e}\n"


def _exec_code_on_remote(code: str, remotes: Optional[Iterable[str]] = None) -> str:
    """Execute arbitrary Python source code on one or more remotes.

    Args:
        code: Python source to run on the target remotes.
        remotes: None for all configured remotes; a remote name (str); or an
                 iterable of remote names.

    Returns:
        Concatenated stdout from all remotes in order.
    """
    outputs: List[str] = []
    for _remote, out in _iter_remote_outputs(code, remotes):
        outputs.append(out)
    return ''.join(outputs)




def exec_on_remote(func: Callable, remotes: Optional[Iterable[str]] = None, *, separators: Optional[bool] = None) -> None:
    """Execute a Python function on the specified remote(s).

    Prints the remote stdout naturally (no quotes, real newlines) and returns None.
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

    if not auto_sep:
        out = _exec_code_on_remote(code, remote_list)
        if out:
            print(out, end='')
        return None

    # With separators: print per-remote with a clear header
    for remote_name, out in _iter_remote_outputs(code, remote_list):
        header = f"\n----- [ {remote_name} ] " + "-" * 40
        print(header)
        if out:
            print(out, end='')
    return None


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
        - Prints stdout in natural form (no quotes) and returns None.
    """
    if not isinstance(code, str):
        raise TypeError("code must be a string containing Python source code")

    remote_list = _resolve_remote_list(remotes)
    auto_sep = (separators if separators is not None else len(remote_list) > 1)

    if not auto_sep:
        out = _exec_code_on_remote(code, remote_list)
        if out:
            print(out, end='')
        return None

    for remote_name, out in _iter_remote_outputs(code, remote_list):
        header = f"\n----- [ {remote_name} ] " + "-" * 40
        print(header)
        if out:
            print(out, end='')
    return None