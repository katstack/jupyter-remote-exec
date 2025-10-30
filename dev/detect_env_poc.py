"""
환경 감지 PoC - 터미널 vs Jupyter
"""


def detect_environment() -> str:
    """Jupyter인지 터미널인지 감지"""
    try:
        # Jupyter/IPython 환경에서만 get_ipython()이 존재
        shell = get_ipython().__class__.__name__
        if shell in ['ZMQInteractiveShell', 'Shell']:
            return 'jupyter'
        elif shell == 'TerminalInteractiveShell':
            return 'ipython'
    except NameError:
        # get_ipython()이 없으면 일반 Python
        pass

    return 'terminal'


def main():
    env = detect_environment()

    print(f"환경: {env}")
    print()

    if env == 'jupyter':
        print("✅ Jupyter Notebook/Lab 환경")
        print("   → ipywidgets 사용")
    elif env == 'ipython':
        print("✅ IPython 터미널 환경")
        print("   → Rich 사용 (터미널과 동일)")
    else:
        print("✅ 일반 Python 터미널 환경")
        print("   → Rich 사용")

    # 추가 정보
    try:
        shell = get_ipython()
        print(f"\nShell 클래스: {shell.__class__.__name__}")
        print(f"Shell 타입: {type(shell)}")
    except NameError:
        print("\nget_ipython() 없음 (일반 Python)")


if __name__ == "__main__":
    main()
