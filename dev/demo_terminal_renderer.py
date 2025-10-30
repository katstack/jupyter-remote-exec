"""
TerminalRenderer 데모 스크립트

실제 WebSocket 호출 없이 시뮬레이션으로 렌더링 테스트
"""
import time
import random
from io import StringIO

from jupyter_remote_exec.parallel import ParallelExecutor, RendererFactory


def simulate_remote_task(remote_name: str, buffer: StringIO, duration: int = 5):
    """리모트 실행 시뮬레이션"""
    # 시작 지연
    time.sleep(random.uniform(0.1, 0.5))
    buffer.write(f"🚀 Starting execution on {remote_name}\n")
    buffer.write(f"Connecting to {remote_name}.compute.example.com...\n")
    buffer.write(f"Initializing kernel...\n\n")

    # 실행 시뮬레이션
    iterations = 10
    for i in range(iterations):
        time.sleep(duration / iterations)

        # 랜덤 로그 타입
        log_type = random.choice(['info', 'data', 'progress'])

        if log_type == 'info':
            buffer.write(f"[INFO] Processing step {i+1}/{iterations}\n")
        elif log_type == 'data':
            buffer.write(f"[DATA] Records processed: {random.randint(1000, 9999)}\n")
        else:
            buffer.write(f"[PROGRESS] {int((i+1)/iterations*100)}% complete\n")

    # 완료
    buffer.write(f"\n✅ Execution completed on {remote_name}\n")
    buffer.write(f"Total time: {duration:.1f}s\n")


def main():
    print("=" * 80)
    print("TerminalRenderer Demo - Parallel Execution Simulation")
    print("=" * 80)
    print()

    # 리모트 목록
    remotes = [
        "us-east-1",
        "us-west-2",
        "eu-west-1",
        "eu-central-1",
        "ap-northeast-1",
        "ap-southeast-1",
        "ap-south-1",
        "sa-east-1",
        "ca-central-1",
        "me-south-1",
        "af-south-1"
    ]

    # 렌더러 생성 (terminal 강제 지정)
    renderer = RendererFactory.create(renderer_type='terminal')

    # ParallelExecutor 생성
    executor = ParallelExecutor(
        renderer=renderer,
        refresh_rate=0.5,  # 깜빡임 감소를 위해 0.5초로 설정
        save_logs=True,
        log_dir="./logs"
    )

    # 실행
    buffers = executor.execute(
        remotes=remotes,
        task_func=simulate_remote_task,
        duration=6
    )

    # 완료 후 전체 로그 표시 (선택)
    print()
    print("=" * 80)
    print("Show full logs? (y/n): ", end="")

    # 자동으로 y 입력 (데모용)
    import sys
    if sys.stdin.isatty():
        choice = input().lower()
    else:
        choice = 'n'
        print('n (auto)')

    if choice == 'y':
        renderer.show_logs(buffers)

    print()
    print("=" * 80)
    print("✅ Demo completed!")
    print("💡 Tip: Check ./logs/session_YYYYMMDD_HHMMSS/ for saved logs")
    print("=" * 80)


if __name__ == "__main__":
    main()
