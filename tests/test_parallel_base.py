"""Tests for parallel execution base classes."""

import pytest
from io import StringIO
from unittest.mock import MagicMock, patch

from jupyter_remote_exec.parallel import BaseRenderer, RendererFactory, ParallelExecutor


class MockRenderer(BaseRenderer):
    """테스트용 Mock 렌더러"""

    def __init__(self):
        self.initialized = False
        self.updates = []
        self.finalized = False
        self.logs_shown = False
        self.cleaned_up = False

    def initialize(self, remotes: list[str]) -> None:
        self.initialized = True
        self.remotes = remotes

    def update(self, remote: str, content: str, status: str) -> None:
        self.updates.append({'remote': remote, 'content': content, 'status': status})

    def finalize(self, buffers: dict) -> None:
        self.finalized = True
        self.buffers = buffers

    def show_logs(self, buffers: dict) -> None:
        self.logs_shown = True

    def cleanup(self) -> None:
        self.cleaned_up = True


def test_base_renderer_is_abstract():
    """BaseRenderer는 추상 클래스여야 함"""
    with pytest.raises(TypeError):
        BaseRenderer()


def test_mock_renderer_implements_interface():
    """MockRenderer가 인터페이스를 올바르게 구현했는지 확인"""
    renderer = MockRenderer()

    # 초기화
    renderer.initialize(['remote1', 'remote2'])
    assert renderer.initialized
    assert renderer.remotes == ['remote1', 'remote2']

    # 업데이트
    renderer.update('remote1', 'output', 'running')
    assert len(renderer.updates) == 1
    assert renderer.updates[0] == {
        'remote': 'remote1',
        'content': 'output',
        'status': 'running'
    }

    # 최종화
    buffers = {'remote1': StringIO('test')}
    renderer.finalize(buffers)
    assert renderer.finalized
    assert renderer.buffers == buffers

    # 로그 표시
    renderer.show_logs(buffers)
    assert renderer.logs_shown

    # 정리
    renderer.cleanup()
    assert renderer.cleaned_up


def test_renderer_factory_auto_detection():
    """RendererFactory가 환경을 자동 감지하는지 확인"""
    # 환경 감지 모킹
    with patch('jupyter_remote_exec.parallel.factory.detect_environment') as mock_detect:
        # 터미널 환경
        mock_detect.return_value = 'terminal'

        # TerminalRenderer가 없으면 ImportError 발생
        with pytest.raises(ImportError, match="Terminal renderer requires 'rich'"):
            RendererFactory.create()

        # Jupyter 환경
        mock_detect.return_value = 'jupyter'

        # JupyterRenderer가 없으면 ImportError 발생
        with pytest.raises(ImportError, match="Jupyter renderer requires 'ipywidgets'"):
            RendererFactory.create()


def test_renderer_factory_explicit_type():
    """RendererFactory에 명시적으로 타입 지정"""
    # 잘못된 타입
    with pytest.raises(ValueError, match="Unknown renderer type"):
        RendererFactory.create(renderer_type='invalid')


def test_parallel_executor_initialization():
    """ParallelExecutor 초기화 테스트"""
    mock_renderer = MockRenderer()
    executor = ParallelExecutor(
        renderer=mock_renderer,
        refresh_rate=0.1,
        save_logs=False
    )

    assert executor.renderer == mock_renderer
    assert executor.refresh_rate == 0.1
    assert executor.save_logs is False


def test_parallel_executor_execute():
    """ParallelExecutor 실행 테스트"""
    mock_renderer = MockRenderer()
    executor = ParallelExecutor(
        renderer=mock_renderer,
        refresh_rate=0.1,
        save_logs=False
    )

    # 테스트용 태스크 함수
    def mock_task(remote: str, buffer: StringIO, message: str = ""):
        buffer.write(f"{remote}: {message}\n")

    # 실행
    remotes = ['remote1', 'remote2']
    buffers = executor.execute(remotes, mock_task, message="test")

    # 검증
    assert mock_renderer.initialized
    assert mock_renderer.remotes == remotes
    assert len(mock_renderer.updates) > 0  # 업데이트가 발생했는지
    assert mock_renderer.finalized
    assert mock_renderer.cleaned_up

    # 버퍼 내용 확인
    assert 'remote1' in buffers
    assert 'remote2' in buffers
    assert 'remote1: test' in buffers['remote1'].getvalue()
    assert 'remote2: test' in buffers['remote2'].getvalue()


def test_parallel_executor_status_determination():
    """상태 결정 로직 테스트"""
    mock_renderer = MockRenderer()
    executor = ParallelExecutor(renderer=mock_renderer, save_logs=False)

    remotes = ['remote1']
    threads = [MagicMock()]

    # Waiting 상태
    threads[0].is_alive.return_value = True
    status = executor._determine_status('', 'remote1', threads, remotes)
    assert status == 'waiting'

    # Running 상태
    status = executor._determine_status('some output', 'remote1', threads, remotes)
    assert status == 'running'

    # Completed 상태
    threads[0].is_alive.return_value = False
    status = executor._determine_status('completed output', 'remote1', threads, remotes)
    assert status == 'completed'

    # Error 상태
    status = executor._determine_status('ERROR occurred', 'remote1', threads, remotes)
    assert status == 'error'

    status = executor._determine_status('Exception raised', 'remote1', threads, remotes)
    assert status == 'error'


def test_parallel_executor_log_saving(tmp_path):
    """로그 저장 테스트"""
    mock_renderer = MockRenderer()
    executor = ParallelExecutor(
        renderer=mock_renderer,
        save_logs=True,
        log_dir=str(tmp_path)
    )

    # 테스트용 태스크
    def mock_task(remote: str, buffer: StringIO):
        buffer.write(f"Log from {remote}\n")

    # 실행
    remotes = ['remote1', 'remote2']
    executor.execute(remotes, mock_task)

    # 로그 파일 확인
    log_dirs = list(tmp_path.glob('session_*'))
    assert len(log_dirs) == 1

    session_dir = log_dirs[0]
    log_files = list(session_dir.glob('*.log'))
    assert len(log_files) == 2

    # 내용 확인
    remote1_log = session_dir / 'remote1.log'
    remote2_log = session_dir / 'remote2.log'

    assert remote1_log.exists()
    assert remote2_log.exists()
    assert 'Log from remote1' in remote1_log.read_text()
    assert 'Log from remote2' in remote2_log.read_text()
