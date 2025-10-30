"""Jupyter renderer using ipywidgets."""

from typing import Dict
from io import StringIO

import ipywidgets as widgets
from IPython.display import display, HTML

from .base import BaseRenderer


class JupyterRenderer(BaseRenderer):
    """
    ipywidgets를 사용한 Jupyter 렌더러.

    HTML 위젯을 직접 업데이트하여 깜빡임 없는 실시간 업데이트를 제공합니다.
    """

    def __init__(
        self,
        max_height: int = 200,
        show_line_count: bool = True
    ):
        """
        JupyterRenderer 초기화.

        Args:
            max_height: 로그 영역 최대 높이 (px)
            show_line_count: 상태에 줄 수 표시 여부
        """
        self.max_height = max_height
        self.show_line_count = show_line_count

        self.remotes: list[str] = []
        self.widgets_dict: Dict[str, dict] = {}
        self.main_box = None

        # 상태별 색상 (HTML 색상)
        self.colors = {
            'waiting': 'orange',
            'running': '#17a2b8',  # cyan
            'completed': 'green',
            'error': 'red'
        }

    def initialize(self, remotes: list[str]) -> None:
        """위젯 생성 및 디스플레이"""
        self.remotes = remotes

        boxes = []
        for remote in remotes:
            # 상태 레이블 (HTML)
            status_label = widgets.HTML(
                value=f"<b style='color: {self.colors['waiting']};'>⏳ {remote} - Waiting...</b>"
            )

            # 로그 내용 (HTML) - 깜빡임 없이 업데이트
            log_content = widgets.HTML(
                value=self._create_log_html("No output yet...")
            )

            # 박스 레이아웃
            box = widgets.VBox([status_label, log_content])
            box.layout.border = f"2px solid {self.colors['waiting']}"
            box.layout.padding = '10px'
            box.layout.margin = '5px'
            box.layout.border_radius = '5px'

            # 위젯 저장
            self.widgets_dict[remote] = {
                'status': status_label,
                'log': log_content,
                'box': box
            }
            boxes.append(box)

        # 전체 레이아웃 디스플레이
        self.main_box = widgets.VBox(boxes)
        display(self.main_box)

    def update(self, remote: str, content: str, status: str) -> None:
        """리모트 상태 업데이트"""
        if remote not in self.widgets_dict:
            return

        w = self.widgets_dict[remote]
        color = self.colors.get(status, 'gray')

        # 상태 이모지
        status_emoji = {
            'waiting': '⏳',
            'running': '⏳',
            'completed': '✅',
            'error': '❌'
        }.get(status, '•')

        # 상태 텍스트
        if self.show_line_count and content:
            line_count = content.count('\n')
            status_text = f"{status_emoji} {remote} - {status.capitalize()} ({line_count} lines)"
        else:
            status_text = f"{status_emoji} {remote} - {status.capitalize()}"

        # 상태 레이블 업데이트
        w['status'].value = f"<b style='color: {color};'>{status_text}</b>"

        # 박스 테두리 색상 업데이트
        w['box'].layout.border = f"2px solid {color}"

        # 로그 내용 업데이트 (HTML 직접 덮어쓰기 - 깜빡임 없음)
        display_content = content if content else "No output yet..."
        w['log'].value = self._create_log_html(display_content)

    def finalize(self, buffers: Dict[str, StringIO]) -> None:
        """완료 메시지 표시"""
        # Jupyter에서는 위젯이 이미 표시되어 있으므로
        # 별도의 완료 메시지는 표시하지 않음
        pass

    def show_logs(self, buffers: Dict[str, StringIO]) -> None:
        """접을 수 있는 전체 로그 표시"""
        html = "<h3>📋 Complete Logs (Click to expand)</h3>"

        for remote in self.remotes:
            if remote not in buffers:
                continue

            content = buffers[remote].getvalue()
            escaped = self._escape_html(content)
            line_count = content.count('\n')

            html += f"""
            <details style="margin: 10px 0; border: 2px solid #28a745; padding: 10px; border-radius: 5px;">
                <summary style="cursor: pointer; font-weight: bold; color: #28a745; padding: 5px;">
                    📍 {remote} ({line_count} lines)
                </summary>
                <pre style="margin-top: 10px; background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; font-family: monospace; font-size: 12px;">{escaped}</pre>
            </details>
            """

        display(HTML(html))

    def cleanup(self) -> None:
        """리소스 정리 (Jupyter에서는 특별히 할 일 없음)"""
        pass

    def _create_log_html(self, content: str) -> str:
        """로그 내용을 HTML로 변환"""
        escaped = self._escape_html(content)
        return f"""<pre style='margin: 0; padding: 8px; background: #f5f5f5;
                    max-height: {self.max_height}px; overflow-y: auto;
                    font-family: monospace; font-size: 12px;'>{escaped}</pre>"""

    def _escape_html(self, text: str) -> str:
        """HTML 특수 문자 이스케이프"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))
