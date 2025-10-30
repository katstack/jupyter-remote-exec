"""Tests for JupyterRenderer."""

import pytest
from io import StringIO
from unittest.mock import MagicMock, patch

# ipywidgets가 없을 수도 있으므로 skip 처리
pytest.importorskip("ipywidgets")

from jupyter_remote_exec.parallel.jupyter import JupyterRenderer


def test_jupyter_renderer_initialization():
    """JupyterRenderer 초기화 테스트"""
    renderer = JupyterRenderer(max_height=300, show_line_count=False)

    assert renderer.max_height == 300
    assert renderer.show_line_count is False
    assert len(renderer.widgets_dict) == 0
    assert renderer.main_box is None


def test_color_mapping():
    """상태별 색상 매핑 테스트"""
    renderer = JupyterRenderer()

    assert renderer.colors['waiting'] == 'orange'
    assert renderer.colors['running'] == '#17a2b8'
    assert renderer.colors['completed'] == 'green'
    assert renderer.colors['error'] == 'red'


def test_escape_html():
    """HTML 이스케이프 테스트"""
    renderer = JupyterRenderer()

    # 기본 이스케이프
    assert renderer._escape_html('<div>') == '&lt;div&gt;'
    assert renderer._escape_html('a & b') == 'a &amp; b'
    assert renderer._escape_html('<script>alert("xss")</script>') == \
           '&lt;script&gt;alert("xss")&lt;/script&gt;'

    # 복합 케이스
    text = 'Hello <world> & friends'
    expected = 'Hello &lt;world&gt; &amp; friends'
    assert renderer._escape_html(text) == expected


def test_create_log_html():
    """로그 HTML 생성 테스트"""
    renderer = JupyterRenderer(max_height=250)

    html = renderer._create_log_html("test output")

    assert 'test output' in html
    assert 'max-height: 250px' in html
    assert '<pre' in html
    assert 'overflow-y: auto' in html


def test_create_log_html_escapes_content():
    """로그 HTML이 내용을 이스케이프하는지 테스트"""
    renderer = JupyterRenderer()

    html = renderer._create_log_html("<script>alert('xss')</script>")

    # HTML이 이스케이프되어야 함
    assert '&lt;script&gt;' in html
    assert '<script>' not in html or html.count('<pre') == 1  # pre 태그만 있어야 함


@patch('jupyter_remote_exec.parallel.jupyter.display')
def test_initialize(mock_display):
    """initialize 메서드 테스트"""
    renderer = JupyterRenderer()
    remotes = ['remote1', 'remote2']

    renderer.initialize(remotes)

    # 상태 확인
    assert renderer.remotes == remotes
    assert len(renderer.widgets_dict) == 2
    assert 'remote1' in renderer.widgets_dict
    assert 'remote2' in renderer.widgets_dict

    # 각 리모트별 위젯 확인
    for remote in remotes:
        w = renderer.widgets_dict[remote]
        assert 'status' in w
        assert 'log' in w
        assert 'box' in w

    # display가 호출되었는지 확인
    mock_display.assert_called_once()


@patch('jupyter_remote_exec.parallel.jupyter.display')
def test_update(mock_display):
    """update 메서드 테스트"""
    renderer = JupyterRenderer()
    remotes = ['remote1']

    renderer.initialize(remotes)

    # Waiting 상태
    renderer.update('remote1', '', 'waiting')
    w = renderer.widgets_dict['remote1']
    assert 'Waiting' in w['status'].value
    assert 'orange' in w['box'].layout.border

    # Running 상태
    renderer.update('remote1', 'output line 1\noutput line 2', 'running')
    assert 'Running' in w['status'].value
    assert '#17a2b8' in w['box'].layout.border

    # Completed 상태
    renderer.update('remote1', 'final output', 'completed')
    assert 'Completed' in w['status'].value
    assert 'green' in w['box'].layout.border

    # Error 상태
    renderer.update('remote1', 'error output', 'error')
    assert 'Error' in w['status'].value
    assert 'red' in w['box'].layout.border


@patch('jupyter_remote_exec.parallel.jupyter.display')
def test_update_with_line_count(mock_display):
    """줄 수 표시 테스트"""
    renderer = JupyterRenderer(show_line_count=True)
    remotes = ['remote1']

    renderer.initialize(remotes)

    content = 'line1\nline2\nline3\n'
    renderer.update('remote1', content, 'running')

    w = renderer.widgets_dict['remote1']
    # 줄 수가 표시되어야 함
    assert 'lines' in w['status'].value.lower()


@patch('jupyter_remote_exec.parallel.jupyter.display')
def test_finalize(mock_display):
    """finalize 메서드 테스트"""
    renderer = JupyterRenderer()
    remotes = ['remote1']

    renderer.initialize(remotes)
    buffers = {'remote1': StringIO('test')}

    # Jupyter에서는 finalize가 특별히 하는 일이 없음
    renderer.finalize(buffers)

    # 에러 없이 실행되는지만 확인
    assert True


@patch('jupyter_remote_exec.parallel.jupyter.display')
def test_show_logs(mock_display):
    """show_logs 메서드 테스트"""
    renderer = JupyterRenderer()
    remotes = ['remote1', 'remote2']

    renderer.initialize(remotes)

    buffers = {
        'remote1': StringIO('output1\noutput2'),
        'remote2': StringIO('output3')
    }

    renderer.show_logs(buffers)

    # display가 HTML과 함께 호출되었는지 확인
    # initialize에서 1번, show_logs에서 1번
    assert mock_display.call_count == 2


@patch('jupyter_remote_exec.parallel.jupyter.display')
def test_cleanup(mock_display):
    """cleanup 메서드 테스트"""
    renderer = JupyterRenderer()
    remotes = ['remote1']

    renderer.initialize(remotes)
    renderer.cleanup()

    # Jupyter에서는 cleanup이 특별히 하는 일이 없음
    # 에러 없이 실행되는지만 확인
    assert True


@patch('jupyter_remote_exec.parallel.jupyter.display')
def test_update_nonexistent_remote(mock_display):
    """존재하지 않는 리모트 업데이트 시도"""
    renderer = JupyterRenderer()
    renderer.initialize(['remote1'])

    # 존재하지 않는 리모트 업데이트 - 에러 없이 무시되어야 함
    renderer.update('nonexistent', 'content', 'running')

    assert True
