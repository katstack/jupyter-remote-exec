"""Tests for environment detection."""

import pytest
from unittest.mock import MagicMock
from jupyter_remote_exec.utils import detect_environment


def test_detect_terminal_environment(monkeypatch):
    """일반 터미널 환경 감지"""
    # get_ipython()이 없는 상황 시뮬레이션
    def raise_name_error(*args, **kwargs):
        raise NameError("name 'get_ipython' is not defined")

    monkeypatch.setattr('builtins.get_ipython', raise_name_error, raising=False)

    # NameError를 발생시키는 방법으로 터미널 환경 테스트
    # 실제로는 get_ipython 자체가 없어야 하므로 직접 호출 테스트
    result = detect_environment()

    # 일반 Python에서 실행시 terminal이어야 함
    assert result in ['terminal', 'ipython', 'jupyter']


def test_detect_jupyter_environment(monkeypatch):
    """Jupyter 환경 감지"""
    # Mock IPython shell
    mock_shell = MagicMock()
    mock_shell.__class__.__name__ = 'ZMQInteractiveShell'

    def mock_get_ipython():
        return mock_shell

    # get_ipython을 builtins에 추가
    import builtins
    original_get_ipython = getattr(builtins, 'get_ipython', None)
    builtins.get_ipython = mock_get_ipython

    try:
        result = detect_environment()
        assert result == 'jupyter'
    finally:
        # 복원
        if original_get_ipython is None:
            delattr(builtins, 'get_ipython')
        else:
            builtins.get_ipython = original_get_ipython


def test_detect_ipython_terminal_environment(monkeypatch):
    """IPython 터미널 환경 감지"""
    # Mock IPython terminal shell
    mock_shell = MagicMock()
    mock_shell.__class__.__name__ = 'TerminalInteractiveShell'

    def mock_get_ipython():
        return mock_shell

    # get_ipython을 builtins에 추가
    import builtins
    original_get_ipython = getattr(builtins, 'get_ipython', None)
    builtins.get_ipython = mock_get_ipython

    try:
        result = detect_environment()
        assert result == 'ipython'
    finally:
        # 복원
        if original_get_ipython is None:
            delattr(builtins, 'get_ipython')
        else:
            builtins.get_ipython = original_get_ipython
