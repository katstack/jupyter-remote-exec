"""Parallel execution orchestrator."""

import time
import threading
from io import StringIO
from pathlib import Path
from datetime import datetime
from typing import Dict, Callable, Optional, Any

from .base import BaseRenderer
from .factory import RendererFactory


class ParallelExecutor:
    """
    여러 리모트에서 병렬로 코드를 실행하고 결과를 렌더링하는 오케스트레이터.
    """

    def __init__(
        self,
        renderer: Optional[BaseRenderer] = None,
        refresh_rate: float = 0.5,
        save_logs: bool = True,
        log_dir: str = "./logs"
    ):
        """
        ParallelExecutor 초기화.

        Args:
            renderer: 사용할 렌더러 (None이면 자동 감지)
            refresh_rate: 업데이트 간격 (초) - 기본 0.5초 (깜빡임 감소)
            save_logs: 로그 파일 저장 여부
            log_dir: 로그 저장 디렉토리
        """
        self.renderer = renderer or RendererFactory.create()
        self.refresh_rate = refresh_rate
        self.save_logs = save_logs
        self.log_dir = Path(log_dir)

    def execute(
        self,
        remotes: list[str],
        task_func: Callable[[str, StringIO], None],
        **task_kwargs: Any
    ) -> Dict[str, StringIO]:
        """
        여러 리모트에서 병렬로 작업 실행.

        Args:
            remotes: 리모트 이름 리스트
            task_func: 각 리모트에서 실행할 함수
                      시그니처: func(remote_name: str, buffer: StringIO, **kwargs)
            **task_kwargs: task_func에 전달할 추가 인자

        Returns:
            Dict[str, StringIO]: 각 리모트별 출력 버퍼
        """
        # 버퍼 초기화
        buffers = {remote: StringIO() for remote in remotes}

        # 렌더러 초기화
        self.renderer.initialize(remotes)

        # 스레드 생성
        threads = []
        for remote in remotes:
            thread = threading.Thread(
                target=task_func,
                args=(remote, buffers[remote]),
                kwargs=task_kwargs,
                daemon=True
            )
            threads.append(thread)

        # 스레드 시작
        for thread in threads:
            thread.start()

        # 실시간 업데이트 루프
        while any(t.is_alive() for t in threads):
            for remote in remotes:
                content = buffers[remote].getvalue()
                status = self._determine_status(content, remote, threads, remotes)

                self.renderer.update(remote, content, status)

            time.sleep(self.refresh_rate)

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join(timeout=1)

        # 최종 업데이트
        for remote in remotes:
            content = buffers[remote].getvalue()
            status = self._determine_status(content, remote, threads, remotes)
            self.renderer.update(remote, content, status)

        # 최종 결과 표시
        self.renderer.finalize(buffers)

        # 로그 저장
        if self.save_logs:
            self._save_logs(buffers)

        # 정리
        self.renderer.cleanup()

        return buffers

    def _determine_status(
        self,
        content: str,
        remote: str,
        threads: list[threading.Thread],
        remotes: list[str]
    ) -> str:
        """
        리모트의 현재 상태 결정.

        Args:
            content: 현재까지의 출력 내용
            remote: 리모트 이름
            threads: 모든 스레드 리스트
            remotes: 모든 리모트 이름 리스트

        Returns:
            str: 'waiting', 'running', 'completed', 'error'
        """
        # 에러 체크 (출력에 특정 키워드 포함 여부)
        if any(keyword in content for keyword in ['ERROR', 'Exception', 'Traceback']):
            return 'error'

        # 완료 체크
        remote_idx = remotes.index(remote)
        if remote_idx < len(threads) and not threads[remote_idx].is_alive():
            return 'completed' if content else 'error'

        # 실행 중 또는 대기 중
        return 'running' if content else 'waiting'

    def _save_logs(self, buffers: Dict[str, StringIO]) -> None:
        """
        로그를 파일로 저장.

        Args:
            buffers: 각 리모트별 출력 버퍼
        """
        # 세션 디렉토리 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.log_dir / f"session_{timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)

        # 각 리모트별 로그 파일 저장
        for remote, buffer in buffers.items():
            log_file = session_dir / f"{remote}.log"
            log_file.write_text(buffer.getvalue())
