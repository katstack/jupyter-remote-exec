"""Environment detection utilities."""


def detect_environment() -> str:
    """
    Detect the current execution environment.

    Returns:
        str: 'jupyter' for Jupyter Notebook/Lab,
             'ipython' for IPython terminal,
             'terminal' for regular Python terminal
    """
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
