"""Base renderer interface for parallel execution."""

from abc import ABC, abstractmethod
from typing import Dict
from io import StringIO


class BaseRenderer(ABC):
    """
    추상 베이스 렌더러 클래스.

    터미널과 Jupyter 환경에서 병렬 실행 결과를 표시하기 위한
    공통 인터페이스를 정의합니다.
    """

    @abstractmethod
    def initialize(self, remotes: list[str]) -> None:
        """
        렌더러 초기화 및 UI 컴포넌트 설정.

        Args:
            remotes: 리모트 이름 리스트
        """
        pass

    @abstractmethod
    def update(self, remote: str, content: str, status: str) -> None:
        """
        특정 리모트의 디스플레이 업데이트.

        Args:
            remote: 리모트 이름
            content: 현재까지의 출력 내용
            status: 'waiting', 'running', 'completed', 'error' 중 하나
        """
        pass

    @abstractmethod
    def finalize(self, buffers: Dict[str, StringIO]) -> None:
        """
        모든 실행 완료 후 최종 결과 표시.

        Args:
            buffers: 각 리모트별 전체 출력 버퍼
        """
        pass

    @abstractmethod
    def show_logs(self, buffers: Dict[str, StringIO]) -> None:
        """
        전체 로그를 접을 수 있는 형태로 표시.

        Args:
            buffers: 각 리모트별 전체 출력 버퍼
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        렌더러 정리 (리소스 해제 등).
        """
        pass
