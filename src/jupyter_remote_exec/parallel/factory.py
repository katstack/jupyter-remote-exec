"""Renderer factory for automatic environment detection."""

from .base import BaseRenderer
from ..utils import detect_environment


class RendererFactory:
    """
    환경에 맞는 렌더러를 자동으로 생성하는 팩토리 클래스.
    """

    @staticmethod
    def create(renderer_type: str = None) -> BaseRenderer:
        """
        환경에 맞는 렌더러 생성.

        Args:
            renderer_type: 강제로 사용할 렌더러 타입
                          ('terminal', 'jupyter', None)
                          None이면 자동 감지

        Returns:
            BaseRenderer: 환경에 맞는 렌더러 인스턴스

        Raises:
            ImportError: 필요한 라이브러리가 없을 때
            ValueError: 알 수 없는 renderer_type일 때
        """
        # 자동 감지 또는 강제 지정
        if renderer_type is None:
            env = detect_environment()
            # ipython도 터미널로 처리
            renderer_type = 'jupyter' if env == 'jupyter' else 'terminal'

        # 렌더러 타입 검증
        if renderer_type not in ['terminal', 'jupyter']:
            raise ValueError(
                f"Unknown renderer type: {renderer_type}. "
                f"Must be 'terminal' or 'jupyter'"
            )

        # 렌더러 생성
        if renderer_type == 'jupyter':
            try:
                from .jupyter import JupyterRenderer
                return JupyterRenderer()
            except ImportError as e:
                raise ImportError(
                    "Jupyter renderer requires 'ipywidgets'. "
                    "Install it with: pip install ipywidgets"
                ) from e
        else:  # terminal
            try:
                from .terminal import TerminalRenderer
                return TerminalRenderer()
            except ImportError as e:
                raise ImportError(
                    "Terminal renderer requires 'rich'. "
                    "Install it with: pip install rich"
                ) from e
