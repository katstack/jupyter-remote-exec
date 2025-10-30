"""
Live 완료 후 전체 로그 출력 + 파일 저장 PoC
"""
import time
import random
import threading
from io import StringIO
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.rule import Rule
from rich.syntax import Syntax


def simulate_remote_execution(remote_name: str, buffer: StringIO, duration: int):
    """많은 로그를 생성하는 시뮬레이션"""
    time.sleep(random.uniform(0.1, 0.3))
    buffer.write(f"🚀 Starting execution on {remote_name}\n")
    buffer.write(f"Connecting to {remote_name}.compute.amazonaws.com...\n")
    buffer.write(f"Initializing kernel...\n\n")

    # 많은 로그 생성
    for i in range(20):
        time.sleep(duration / 20)

        if i % 5 == 0:
            buffer.write(f"\n=== Phase {i//5 + 1} ===\n")

        log_type = random.choice(['info', 'data', 'metric'])

        if log_type == 'info':
            buffer.write(f"[INFO] Processing batch {i+1}/20\n")
        elif log_type == 'data':
            buffer.write(f"[DATA] Records processed: {random.randint(1000, 9999)}\n")
        else:
            buffer.write(f"[METRIC] Loss: {random.uniform(0.1, 0.9):.4f}\n")

    buffer.write(f"\n✅ Execution completed on {remote_name}\n")
    buffer.write(f"Total time: {duration:.1f}s\n")


def parallel_with_full_logs(remotes: list[str], duration: int = 4):
    """Live 실행 후 전체 로그 출력"""
    console = Console()

    # 레이아웃 생성
    layout = Layout()
    layout.split_column(*[Layout(name=r) for r in remotes])

    # 버퍼
    buffers = {remote: StringIO() for remote in remotes}

    # 초기화
    for remote in remotes:
        layout[remote].update(
            Panel("⏳ Waiting...", title=f"[yellow]{remote}[/yellow]", border_style="yellow")
        )

    # 스레드
    threads = []
    for remote in remotes:
        thread = threading.Thread(
            target=simulate_remote_execution,
            args=(remote, buffers[remote], duration),
            daemon=True
        )
        threads.append(thread)

    # Live 실행
    console.print("[bold cyan]🚀 Starting parallel execution...[/bold cyan]\n")

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

                # 마지막 10줄만 표시 (Live 중)
                lines = content.splitlines()
                tail = '\n'.join(lines[-10:]) if len(lines) > 10 else content

                layout[remote].update(
                    Panel(
                        tail,
                        title=f"[{color}]{remote}[/{color}] ({len(lines)} lines)",
                        border_style=color
                    )
                )
            time.sleep(0.1)

        for thread in threads:
            thread.join(timeout=1)

    # Live 종료 후 전체 로그 출력
    console.print("\n")
    console.print(Rule("[bold green]✅ All executions completed![/bold green]"))
    console.print("\n")
    console.print("[bold cyan]📋 Complete Logs:[/bold cyan]")
    console.print("\n")

    for remote in remotes:
        console.print(f"\n[bold magenta]{'─' * 60}[/bold magenta]")
        console.print(f"[bold cyan]Region: {remote}[/bold cyan]")
        console.print(f"[bold magenta]{'─' * 60}[/bold magenta]\n")

        # 전체 로그 출력
        full_log = buffers[remote].getvalue()
        console.print(full_log)

    # 로그 파일 저장
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = log_dir / f"session_{timestamp}"
    session_dir.mkdir(exist_ok=True)

    console.print("\n")
    console.print(Rule("[bold yellow]💾 Saving logs to files[/bold yellow]"))
    console.print()

    saved_files = []
    for remote in remotes:
        log_file = session_dir / f"{remote}.log"
        log_file.write_text(buffers[remote].getvalue())
        saved_files.append(log_file)
        console.print(f"  ✅ [cyan]{remote}[/cyan] → {log_file}")

    # 요약
    console.print("\n")
    console.print(Rule("[bold yellow]Summary[/bold yellow]"))
    for remote in remotes:
        lines = buffers[remote].getvalue().splitlines()
        console.print(f"  • [cyan]{remote}[/cyan]: {len(lines)} lines")

    console.print(f"\n  📁 Logs directory: [bold]{session_dir}[/bold]")


if __name__ == "__main__":
    regions = [
        "us-east-1",
        "eu-west-1",
        "ap-northeast-1"
    ]

    print("=" * 80)
    print("Live + Full Logs PoC")
    print("=" * 80)
    print()

    parallel_with_full_logs(regions, duration=5)

    print()
    print("=" * 80)
    print("💡 Tip: 위로 스크롤하면 전체 로그를 볼 수 있습니다!")
    print("=" * 80)
