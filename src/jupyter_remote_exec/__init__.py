"""Jupyter Remote Exec - Execute code on remote Jupyter servers."""

from .core import exec_on_remote, shell_on_remote, get_remotes
from .config import set_config

__version__ = "0.1.0"
__all__ = ["exec_on_remote", "shell_on_remote", "get_remotes", "set_config"]
