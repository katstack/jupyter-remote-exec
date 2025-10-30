"""
Grid 레이아웃 PoC - 11개 리모트를 3열로 배치
"""
import time
import random
import threading
from io import StringIO
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
import math


def simulate_remote_execution(remote_name: str, buffer: StringIO, duration: int):
    """간단한 시뮬레이션"""
    time.sleep(random.uniform(0.1, 0.5))
    buffer.write(f"🚀 {remote_name} started\n")

    iterations = 5
    for i in range(iterations):
        time.sleep(duration / iterations)
        buffer.write(f"[{i+1}/{iterations}] Step {i+1}\n")

    buffer.write(f"✅ Done!\n")


def create_grid_layout(remotes: list[str], cols: int = 3):
    """그리드 레이아웃 생성"""
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


def parallel_execution_grid(remotes: list[str], duration: int = 5):
    """그리드 레이아웃으로 병렬 실행"""
    console = Console()

    # 3열 그리드 레이아웃
    layout = create_grid_layout(remotes, cols=3)

    # 버퍼
    buffers = {remote: StringIO() for remote in remotes}

    # 초기화
    for remote in remotes:
        layout[remote].update(
            Panel("⏳ Waiting...", title=f"[yellow]{remote}[/yellow]",
                  border_style="yellow", padding=(0, 1))
        )

    # 스레드 생성
    threads = []
    for remote in remotes:
        thread = threading.Thread(
            target=simulate_remote_execution,
            args=(remote, buffers[remote], duration),
            daemon=True
        )
        threads.append(thread)

    # Live 업데이트
    with Live(layout, console=console, refresh_per_second=4):
        for thread in threads:
            thread.start()

        while any(t.is_alive() for t in threads):
            for remote in remotes:
                content = buffers[remote].getvalue()
                if not content:
                    continue

                is_complete = "✅" in content
                color = "green" if is_complete else "cyan"

                layout[remote].update(
                    Panel(
                        content.rstrip(),
                        title=f"[{color}]{remote}[/{color}]",
                        border_style=color,
                        padding=(0, 1)
                    )
                )
            time.sleep(0.1)

        for thread in threads:
            thread.join(timeout=1)


if __name__ == "__main__":
    # 11개 리전 시뮬레이션
    regions = [
        "us-east-1",
        "us-west-1",
        "eu-central-1",
        "eu-west-1",
        "ap-northeast-1",
        "ap-southeast-1",
        "ap-south-1",
        "sa-east-1",
        "ca-central-1",
        "me-south-1",
        "af-south-1"
    ]

    print("=" * 80)
    print(f"Grid Layout PoC - {len(regions)} regions in 3 columns")
    print("=" * 80)
    print()

    parallel_execution_grid(regions, duration=6)

    print()
    print("=" * 80)
    print("Done!")
    print("=" * 80)
