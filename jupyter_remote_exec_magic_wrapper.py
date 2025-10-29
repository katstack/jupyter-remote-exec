"""
Jupyter Remote Exec — IPython extension thin wrapper

This file provides a minimal IPython magic adapter around the core library API
(`jupyter_remote_exec.py`). It registers convenient functions into the notebook
namespace when loaded via:
    %load_ext jupyter_remote_exec_magic_wrapper

Author: whya5448
Date: 2025-10-29
Version: 2.0.0
"""

from IPython.core.magic import Magics, magics_class
from jupyter_remote_exec import (
    get_remotes as api_get_remotes,
    exec_on_remote as api_exec_on_remote,
    shell_on_remote as api_exec_cell_on_remote,
)


# ============================================================================
# Magic class (thin wrapper)
# ============================================================================

@magics_class
class RemoteExecMagics(Magics):
    """IPython magic adapter that exposes `exec_on_remote`, `shell_on_remote`, and `get_remotes`.

    The actual implementation lives in `jupyter_remote_exec.py`. This wrapper
    only binds the functions into the user namespace for a convenient notebook
    UX.
    """

    def __init__(self, shell):
        super().__init__(shell)

        # Register helper functions to the notebook global namespace
        shell.user_ns['exec_on_remote'] = api_exec_on_remote
        shell.user_ns['shell_on_remote'] = api_exec_cell_on_remote
        shell.user_ns['get_remotes'] = api_get_remotes

        print(f"✅ jupyter-remote-exec loaded. Available remotes: {api_get_remotes()}")


# ============================================================================
# Extension load/unload
# ============================================================================

def load_ipython_extension(ipython):
    """IPython hook to load this extension via `%load_ext jupyter_remote_exec_magic_wrapper`."""
    ipython.register_magics(RemoteExecMagics)


def unload_ipython_extension(ipython):
    """IPython hook to unload this extension via `%unload_ext jupyter_remote_exec_magic_wrapper`."""
    # Remove helper functions from the global namespace
    for name in (
        'exec_on_remote', 'shell_on_remote', 'get_remotes'
    ):
        try:
            del ipython.user_ns[name]
        except Exception:
            pass
