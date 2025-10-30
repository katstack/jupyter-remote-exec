"""Terminal renderer using Rich library."""

import math
from typing import Dict, Optional
from io import StringIO

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.rule import Rule

from .base import BaseRenderer


class TerminalRenderer(BaseRenderer):
    """
    Rich 라이브러리를 사용한 터미널 렌더러.

    실시간 Live 업데이트와 그리드 레이아웃을 지원합니다.
    """

    def __init__(
        self,
        columns: Optional[int] = None,
        max_lines_live: int = 10,
        show_line_count: bool = True
    ):
        """
        TerminalRenderer 초기화.

        Args:
            columns: 그리드 열 개수 (None이면 자동 감지)
            max_lines_live: Live 중 표시할 최대 줄 수 (0이면 전체 표시)
            show_line_count: 타이틀에 줄 수 표시 여부
        """
        self.columns = columns
        self.max_lines_live = max_lines_live
        self.show_line_count = show_line_count

        self.console = Console()
        self.layout: Optional[Layout] = None
        self.live: Optional[Live] = None
        self.remotes: list[str] = []

        # 상태별 색상
        self.colors = {
            'waiting': 'yellow',
            'running': 'cyan',
            'completed': 'green',
            'error': 'red'
        }

    def initialize(self, remotes: list[str]) -> None:
        """렌더러 초기화 및 레이아웃 생성"""
        self.remotes = remotes

        # 열 개수 자동 감지
        if self.columns is None:
            self.columns = self._auto_detect_columns(len(remotes))

        # 레이아웃 생성
        self.layout = self._create_grid_layout(remotes, self.columns)

        # 초기 상태로 설정
        for remote in remotes:
            self.layout[remote].update(
                Panel(
                    "⏳ Waiting...",
                    title=f"[{self.colors['waiting']}]{remote}[/{self.colors['waiting']}]",
                    border_style=self.colors['waiting'],
                    padding=(0, 1)
                )
            )

        # Live 시작
        self.console.print("[bold cyan]🚀 Starting parallel execution...[/bold cyan]\n")
        self.live = Live(
            self.layout,
            console=self.console,
            refresh_per_second=2,  # 깜빡임 감소를 위해 낮춤 (4 -> 2)
            screen=False,  # 전체 화면 모드 비활성화
            auto_refresh=True
        )
        self.live.start()

    def update(self, remote: str, content: str, status: str) -> None:
        """리모트 상태 업데이트"""
        if self.layout is None or remote not in self.remotes:
            return

        # 색상 선택
        color = self.colors.get(status, 'white')

        # 내용 준비 (max_lines_live 적용)
        if self.max_lines_live > 0 and content:
            lines = content.splitlines()
            if len(lines) > self.max_lines_live:
                display_content = '\n'.join(lines[-self.max_lines_live:])
            else:
                display_content = content
        else:
            display_content = content if content else "No output yet..."

        # 타이틀 준비
        title_parts = [f"[{color}]{remote}[/{color}]"]
        if self.show_line_count and content:
            line_count = content.count('\n')
            title_parts.append(f"({line_count} lines)")
        title = " ".join(title_parts)

        # 상태 이모지
        status_emoji = {
            'waiting': '⏳',
            'running': '⏳',
            'completed': '✅',
            'error': '❌'
        }.get(status, '•')

        # 패널 업데이트
        self.layout[remote].update(
            Panel(
                display_content.rstrip(),
                title=f"{status_emoji} {title}",
                border_style=color,
                padding=(0, 1)
            )
        )

    def finalize(self, buffers: Dict[str, StringIO]) -> None:
        """Live 종료 및 최종 상태 표시"""
        # Live 중지
        if self.live:
            self.live.stop()
            self.live = None

        # 완료 메시지
        self.console.print()
        self.console.print(Rule("[bold green]✅ All executions completed![/bold green]"))
        self.console.print()

    def show_logs(self, buffers: Dict[str, StringIO]) -> None:
        """전체 로그 출력"""
        self.console.print("[bold cyan]📋 Complete Logs:[/bold cyan]")
        self.console.print()

        for remote in self.remotes:
            if remote not in buffers:
                continue

            content = buffers[remote].getvalue()
            line_count = content.count('\n')

            # 구분선
            self.console.print(f"[bold magenta]{'─' * 60}[/bold magenta]")
            self.console.print(f"[bold cyan]Region: {remote}[/bold cyan] ({line_count} lines)")
            self.console.print(f"[bold magenta]{'─' * 60}[/bold magenta]")
            self.console.print()

            # 로그 내용
            self.console.print(content)
            self.console.print()

    def cleanup(self) -> None:
        """리소스 정리"""
        if self.live:
            self.live.stop()
            self.live = None

    def _auto_detect_columns(self, n_remotes: int) -> int:
        """리모트 개수에 따른 최적 열 개수 자동 감지"""
        if n_remotes <= 3:
            return 1
        elif n_remotes <= 6:
            return 2
        else:
            return 3  # 최대 3열

    def _create_grid_layout(self, remotes: list[str], cols: int) -> Layout:
        """그리드 레이아웃 생성"""
        if cols == 1:
            # 단일 열 - 세로로만 나열
            layout = Layout()
            layout.split_column(*[Layout(name=r) for r in remotes])
            return layout

        # 다중 열 - 그리드
        rows = math.ceil(len(remotes) / cols)

        # 메인 레이아웃을 열로 분할
        layout = Layout()
        column_layouts = [Layout(name=f"col{i}") for i in range(cols)]
        layout.split_row(*column_layouts)

        # 각 열을 행으로 분할
        remote_idx = 0
        for col_idx in range(cols):
            row_layouts = []
            for row_idx in range(rows):
                if remote_idx < len(remotes):
                    row_layouts.append(Layout(name=remotes[remote_idx]))
                    remote_idx += 1

            if row_layouts:
                layout[f"col{col_idx}"].split_column(*row_layouts)

        return layout
