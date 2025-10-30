"""Tests for core library API."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from jupyter_remote_exec.core import (
    get_remotes,
    exec_on_remote,
    shell_on_remote,
    _resolve_remote_list,
    _ensure_kernel,
    _active_kernels
)


@pytest.fixture
def clean_active_kernels():
    """Clean active kernels cache before and after each test."""
    _active_kernels.clear()
    yield
    _active_kernels.clear()


class TestGetRemotes:
    """Test the get_remotes function."""

    @patch('jupyter_remote_exec.core.cfg_get_remotes')
    def test_get_remotes(self, mock_cfg_get_remotes):
        mock_cfg_get_remotes.return_value = ['dev', 'prod', 'staging']
        remotes = get_remotes()
        assert remotes == ['dev', 'prod', 'staging']
        assert isinstance(remotes, list)

    @patch('jupyter_remote_exec.core.cfg_get_remotes')
    def test_get_remotes_empty(self, mock_cfg_get_remotes):
        mock_cfg_get_remotes.return_value = []
        remotes = get_remotes()
        assert remotes == []


class TestResolveRemoteList:
    """Test the _resolve_remote_list helper function."""

    @patch('jupyter_remote_exec.core.get_remotes')
    def test_resolve_none_returns_all(self, mock_get_remotes):
        mock_get_remotes.return_value = ['dev', 'prod']
        result = _resolve_remote_list(None)
        assert result == ['dev', 'prod']

    def test_resolve_string_returns_list(self):
        result = _resolve_remote_list('dev')
        assert result == ['dev']

    def test_resolve_iterable_returns_list(self):
        result = _resolve_remote_list(['dev', 'prod'])
        assert result == ['dev', 'prod']

    def test_resolve_tuple_returns_list(self):
        result = _resolve_remote_list(('dev', 'prod'))
        assert result == ['dev', 'prod']


class TestEnsureKernel:
    """Test the _ensure_kernel function."""

    @patch('jupyter_remote_exec.core.materialize_remote')
    @patch('jupyter_remote_exec.core.create_kernel')
    def test_ensure_kernel_success(self, mock_create_kernel, mock_materialize, clean_active_kernels):
        mock_materialize.return_value = {
            'host': 'localhost',
            'port': 8888,
            'https': False,
            'verify': None,
            'token': 'test-token'
        }
        mock_create_kernel.return_value = 'kernel-123'

        result = _ensure_kernel('dev')

        assert result is True
        assert 'dev' in _active_kernels
        assert _active_kernels['dev']['kernel_id'] == 'kernel-123'
        mock_create_kernel.assert_called_once_with(
            'localhost', 8888, 'test-token', https=False, verify=None
        )

    def test_ensure_kernel_already_exists(self, clean_active_kernels):
        _active_kernels['dev'] = {'kernel_id': 'existing-kernel'}

        result = _ensure_kernel('dev')

        assert result is True

    @patch('jupyter_remote_exec.core.materialize_remote')
    def test_ensure_kernel_missing_config(self, mock_materialize, clean_active_kernels, capsys):
        mock_materialize.return_value = None

        result = _ensure_kernel('dev')

        assert result is False
        captured = capsys.readouterr()
        assert "Missing host/port" in captured.out

    @patch('jupyter_remote_exec.core.materialize_remote')
    @patch('jupyter_remote_exec.core.create_kernel')
    def test_ensure_kernel_creation_fails(self, mock_create_kernel, mock_materialize,
                                         clean_active_kernels, capsys):
        from jupyter_remote_exec.http_client import JupyterHTTPError

        mock_materialize.return_value = {
            'host': 'localhost',
            'port': 8888,
            'https': False,
            'verify': None,
            'token': 'token'
        }
        mock_create_kernel.side_effect = JupyterHTTPError("Connection failed")

        result = _ensure_kernel('dev')

        assert result is False
        assert 'dev' not in _active_kernels
        captured = capsys.readouterr()
        assert "Failed to create kernel" in captured.out


class TestExecOnRemote:
    """Test the exec_on_remote function."""

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.execute_code_over_ws')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_exec_on_remote_simple_function(self, mock_get_remotes, mock_execute,
                                           mock_ensure, clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev']
        mock_ensure.return_value = True

        # Mock execute_code_over_ws to write to the file parameter
        def write_to_file(*args, **kwargs):
            file = kwargs.get('file', None)
            if file:
                file.write('Hello from remote\n')
                file.flush()
        mock_execute.side_effect = write_to_file

        _active_kernels['dev'] = {
            'host': 'localhost',
            'port': 8888,
            'https': False,
            'verify': None,
            'token': 'token',
            'kernel_id': 'kernel-123'
        }

        def test_func():
            print("Hello from remote")

        exec_on_remote(test_func, remotes='dev')

        captured = capsys.readouterr()
        assert 'Hello from remote' in captured.out

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.execute_code_over_ws')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_exec_on_remote_with_separator(self, mock_get_remotes, mock_execute,
                                          mock_ensure, clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev', 'prod']
        mock_ensure.return_value = True

        # Mock execute_code_over_ws to write to the file parameter
        def write_to_file(*args, **kwargs):
            file = kwargs.get('file', None)
            if file:
                file.write('output\n')
                file.flush()
        mock_execute.side_effect = write_to_file

        for remote in ['dev', 'prod']:
            _active_kernels[remote] = {
                'host': 'localhost',
                'port': 8888,
                'https': False,
                'verify': None,
                'token': 'token',
                'kernel_id': f'kernel-{remote}'
            }

        def test_func():
            print("output")

        exec_on_remote(test_func, remotes=['dev', 'prod'])

        captured = capsys.readouterr()
        assert '----- [ dev ]' in captured.out
        assert '----- [ prod ]' in captured.out

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.execute_code_over_ws')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_exec_on_remote_no_separator_single(self, mock_get_remotes, mock_execute,
                                               mock_ensure, clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev']
        mock_ensure.return_value = True

        # Mock execute_code_over_ws to write to the file parameter
        def write_to_file(*args, **kwargs):
            file = kwargs.get('file', None)
            if file:
                file.write('output\n')
                file.flush()
        mock_execute.side_effect = write_to_file

        _active_kernels['dev'] = {
            'host': 'localhost',
            'port': 8888,
            'https': False,
            'verify': None,
            'token': 'token',
            'kernel_id': 'kernel-dev'
        }

        def test_func():
            print("output")

        exec_on_remote(test_func, remotes='dev')

        captured = capsys.readouterr()
        assert '-----' not in captured.out
        assert 'output' in captured.out



class TestShellOnRemote:
    """Test the shell_on_remote function."""

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.execute_code_over_ws')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_shell_on_remote_simple_code(self, mock_get_remotes, mock_execute,
                                        mock_ensure, clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev']
        mock_ensure.return_value = True

        # Mock execute_code_over_ws to write to the file parameter
        def write_to_file(*args, **kwargs):
            file = kwargs.get('file', None)
            if file:
                file.write('42\n')
                file.flush()
        mock_execute.side_effect = write_to_file

        _active_kernels['dev'] = {
            'host': 'localhost',
            'port': 8888,
            'https': False,
            'verify': None,
            'token': 'token',
            'kernel_id': 'kernel-123'
        }

        shell_on_remote("print(42)", remotes='dev')

        captured = capsys.readouterr()
        assert '42' in captured.out

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.execute_code_over_ws')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_shell_on_remote_multiline_code(self, mock_get_remotes, mock_execute,
                                           mock_ensure, clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev']
        mock_ensure.return_value = True

        # Mock execute_code_over_ws to write to the file parameter
        def write_to_file(*args, **kwargs):
            file = kwargs.get('file', None)
            if file:
                file.write('3\n')
                file.flush()
        mock_execute.side_effect = write_to_file

        _active_kernels['dev'] = {
            'host': 'localhost',
            'port': 8888,
            'https': False,
            'verify': None,
            'token': 'token',
            'kernel_id': 'kernel-123'
        }

        code = """
x = 1
y = 2
print(x + y)
"""
        shell_on_remote(code, remotes='dev')

        captured = capsys.readouterr()
        assert '3' in captured.out

    def test_shell_on_remote_invalid_code_type(self):
        with pytest.raises(TypeError) as exc_info:
            shell_on_remote(123)  # Not a string

        assert "code must be a string" in str(exc_info.value)

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.execute_code_over_ws')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_shell_on_remote_with_separators(self, mock_get_remotes, mock_execute,
                                            mock_ensure, clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev', 'prod']
        mock_ensure.return_value = True

        # Mock execute_code_over_ws to write to the file parameter
        def write_to_file(*args, **kwargs):
            file = kwargs.get('file', None)
            if file:
                file.write('output\n')
                file.flush()
        mock_execute.side_effect = write_to_file

        for remote in ['dev', 'prod']:
            _active_kernels[remote] = {
                'host': 'localhost',
                'port': 8888,
                'https': False,
                'verify': None,
                'token': 'token',
                'kernel_id': f'kernel-{remote}'
            }

        shell_on_remote("print('output')", remotes=['dev', 'prod'])

        captured = capsys.readouterr()
        assert '----- [ dev ]' in captured.out
        assert '----- [ prod ]' in captured.out

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.execute_code_over_ws')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_shell_on_remote_explicit_separator_false(self, mock_get_remotes, mock_execute,
                                                      mock_ensure, clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev', 'prod']
        mock_ensure.return_value = True

        # Mock execute_code_over_ws to write to the file parameter
        def write_to_file(*args, **kwargs):
            file = kwargs.get('file', None)
            if file:
                file.write('output\n')
                file.flush()
        mock_execute.side_effect = write_to_file

        for remote in ['dev', 'prod']:
            _active_kernels[remote] = {
                'host': 'localhost',
                'port': 8888,
                'https': False,
                'verify': None,
                'token': 'token',
                'kernel_id': f'kernel-{remote}'
            }

        shell_on_remote("print('output')", remotes=['dev', 'prod'], separators=False)

        captured = capsys.readouterr()
        assert '-----' not in captured.out
        assert 'output' in captured.out

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_shell_on_remote_unknown_remote(self, mock_get_remotes, mock_ensure,
                                           clean_active_kernels, capsys):
        mock_get_remotes.return_value = ['dev']

        shell_on_remote("print('test')", remotes='unknown')

        captured = capsys.readouterr()
        assert 'Unknown remote' in captured.out

    @patch('jupyter_remote_exec.core._ensure_kernel')
    @patch('jupyter_remote_exec.core.get_remotes')
    def test_shell_on_remote_kernel_creation_fails(self, mock_get_remotes, mock_ensure,
                                                   clean_active_kernels):
        mock_get_remotes.return_value = ['dev']
        mock_ensure.return_value = False

        shell_on_remote("print('test')", remotes='dev')

        # Should not raise, just return without output


