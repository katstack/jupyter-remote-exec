"""Tests for TerminalRenderer."""

import pytest
from io import StringIO
from unittest.mock import MagicMock, patch

# Rich가 없을 수도 있으므로 skip 처리
pytest.importorskip("rich")

from jupyter_remote_exec.parallel.terminal import TerminalRenderer


def test_terminal_renderer_initialization():
    """TerminalRenderer 초기화 테스트"""
    renderer = TerminalRenderer(columns=2, max_lines_live=5, show_line_count=True)

    assert renderer.columns == 2
    assert renderer.max_lines_live == 5
    assert renderer.show_line_count is True
    assert renderer.console is not None


def test_auto_detect_columns():
    """열 개수 자동 감지 테스트"""
    renderer = TerminalRenderer()

    # 3개 이하 -> 1열
    assert renderer._auto_detect_columns(1) == 1
    assert renderer._auto_detect_columns(3) == 1

    # 4-6개 -> 2열
    assert renderer._auto_detect_columns(4) == 2
    assert renderer._auto_detect_columns(6) == 2

    # 7개 이상 -> 3열
    assert renderer._auto_detect_columns(7) == 3
    assert renderer._auto_detect_columns(11) == 3


def test_create_single_column_layout():
    """단일 열 레이아웃 생성 테스트"""
    renderer = TerminalRenderer()
    remotes = ['remote1', 'remote2', 'remote3']

    layout = renderer._create_grid_layout(remotes, cols=1)

    assert layout is not None
    # 각 리모트가 레이아웃에 존재하는지 확인
    for remote in remotes:
        assert layout[remote] is not None


def test_create_grid_layout():
    """그리드 레이아웃 생성 테스트"""
    renderer = TerminalRenderer()
    remotes = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']

    layout = renderer._create_grid_layout(remotes, cols=3)

    assert layout is not None
    # 각 리모트가 레이아웃에 존재하는지 확인
    for remote in remotes:
        assert layout[remote] is not None


@patch('jupyter_remote_exec.parallel.terminal.Live')
def test_initialize(mock_live_class):
    """initialize 메서드 테스트"""
    mock_live = MagicMock()
    mock_live_class.return_value = mock_live

    renderer = TerminalRenderer(columns=2)
    remotes = ['remote1', 'remote2']

    renderer.initialize(remotes)

    # 상태 확인
    assert renderer.remotes == remotes
    assert renderer.layout is not None
    assert renderer.columns == 2

    # Live가 시작되었는지 확인
    mock_live.start.assert_called_once()


@patch('jupyter_remote_exec.parallel.terminal.Live')
def test_update(mock_live_class):
    """update 메서드 테스트"""
    mock_live = MagicMock()
    mock_live_class.return_value = mock_live

    renderer = TerminalRenderer(max_lines_live=3)
    remotes = ['remote1']

    renderer.initialize(remotes)

    # 짧은 내용 업데이트
    renderer.update('remote1', 'line1\nline2', 'running')

    # 긴 내용 업데이트 (max_lines_live 적용)
    long_content = '\n'.join([f'line{i}' for i in range(10)])
    renderer.update('remote1', long_content, 'completed')

    # 에러 없이 실행되었는지만 확인
    assert True


@patch('jupyter_remote_exec.parallel.terminal.Live')
def test_finalize(mock_live_class):
    """finalize 메서드 테스트"""
    mock_live = MagicMock()
    mock_live_class.return_value = mock_live

    renderer = TerminalRenderer()
    remotes = ['remote1']

    renderer.initialize(remotes)
    buffers = {'remote1': StringIO('test output')}

    renderer.finalize(buffers)

    # Live가 중지되었는지 확인
    mock_live.stop.assert_called_once()
    assert renderer.live is None


@patch('jupyter_remote_exec.parallel.terminal.Live')
def test_show_logs(mock_live_class):
    """show_logs 메서드 테스트"""
    mock_live = MagicMock()
    mock_live_class.return_value = mock_live

    renderer = TerminalRenderer()
    remotes = ['remote1', 'remote2']

    renderer.initialize(remotes)

    buffers = {
        'remote1': StringIO('output1\noutput2'),
        'remote2': StringIO('output3')
    }

    # 에러 없이 실행되는지 확인
    renderer.show_logs(buffers)
    assert True


@patch('jupyter_remote_exec.parallel.terminal.Live')
def test_cleanup(mock_live_class):
    """cleanup 메서드 테스트"""
    mock_live = MagicMock()
    mock_live_class.return_value = mock_live

    renderer = TerminalRenderer()
    remotes = ['remote1']

    renderer.initialize(remotes)
    renderer.cleanup()

    # Live가 중지되었는지 확인
    mock_live.stop.assert_called()
    assert renderer.live is None


def test_color_mapping():
    """상태별 색상 매핑 테스트"""
    renderer = TerminalRenderer()

    assert renderer.colors['waiting'] == 'yellow'
    assert renderer.colors['running'] == 'cyan'
    assert renderer.colors['completed'] == 'green'
    assert renderer.colors['error'] == 'red'
