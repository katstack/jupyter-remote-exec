"""Tests for WebSocket client utilities."""
import pytest
import json
import ssl
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from jupyter_remote_exec.ws_client import execute_code_over_ws, JupyterWSError, DEFAULT_WS_TIMEOUT


class TestExecuteCodeOverWS:
    """Test the execute_code_over_ws function."""

    def _create_mock_message(self, msg_id, msg_type, content):
        """Helper to create a mock Jupyter protocol message."""
        return json.dumps({
            'parent_header': {'msg_id': msg_id},
            'msg_type': msg_type,
            'content': content
        })

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_successful_execution(self, mock_uuid, mock_create_connection):
        # Use fixed UUIDs for testing
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'stream', {'text': 'Hello World\n'}),
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        # Test in collect mode using StringIO
        buffer = StringIO()
        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "print('Hello World')", file=buffer)

        assert 'Hello World\n' in buffer.getvalue()
        mock_create_connection.assert_called_once()
        mock_ws.send.assert_called_once()
        mock_ws.close.assert_called_once()

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_execution_with_multiple_outputs(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'stream', {'text': 'Line 1\n'}),
            self._create_mock_message(msg_id, 'stream', {'text': 'Line 2\n'}),
            self._create_mock_message(msg_id, 'execute_result', {'data': '42'}),
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)
        result = buffer.getvalue()

        assert 'Line 1\n' in result
        assert 'Line 2\n' in result
        assert '42' in result

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_execution_with_error(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'error', {
                'ename': 'NameError',
                'evalue': 'name "x" is not defined',
                'traceback': ['Traceback...', 'Line 1: x']
            }),
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "print(x)", file=buffer)
        result = buffer.getvalue()

        assert 'NameError' in result
        assert 'not defined' in result

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ws_url_construction_http(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", https=False)

        call_args = mock_create_connection.call_args[0]
        url = call_args[0]
        assert url.startswith("ws://")
        assert "token=token" in url
        assert "kernel-123" in url

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ws_url_construction_https(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", https=True)

        call_args = mock_create_connection.call_args[0]
        url = call_args[0]
        assert url.startswith("wss://")

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ws_without_token(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        execute_code_over_ws("localhost", 8888, "kernel-123", None, "code")

        call_args = mock_create_connection.call_args[0]
        url = call_args[0]
        assert "token=" not in url

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ws_with_custom_timeout(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", timeout=60.0)

        call_kwargs = mock_create_connection.call_args[1]
        assert call_kwargs['timeout'] == 60.0

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ws_with_default_timeout(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)

        call_kwargs = mock_create_connection.call_args[1]
        assert call_kwargs['timeout'] == DEFAULT_WS_TIMEOUT

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ws_verify_false(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code",
                           https=True, verify=False)

        call_kwargs = mock_create_connection.call_args[1]
        assert 'sslopt' in call_kwargs
        assert call_kwargs['sslopt']['cert_reqs'] == ssl.CERT_NONE

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ws_verify_with_cert_path(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        cert_path = "/path/to/cert.pem"
        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code",
                           https=True, verify=cert_path)

        call_kwargs = mock_create_connection.call_args[1]
        assert 'sslopt' in call_kwargs
        assert call_kwargs['sslopt']['cert_reqs'] == ssl.CERT_REQUIRED
        assert call_kwargs['sslopt']['ca_certs'] == cert_path

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    def test_ws_connection_error(self, mock_create_connection):
        mock_create_connection.side_effect = Exception("Connection failed")

        buffer = StringIO()
        with pytest.raises(JupyterWSError) as exc_info:
            execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)

        assert "Failed to connect WS" in str(exc_info.value)

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    def test_ws_communication_error(self, mock_create_connection):
        mock_ws = Mock()
        mock_ws.recv.side_effect = Exception("Communication error")
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        with pytest.raises(JupyterWSError) as exc_info:
            execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)

        assert "WS communication error" in str(exc_info.value)
        mock_ws.close.assert_called_once()

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_ignore_messages_with_different_parent(self, mock_uuid, mock_create_connection):
        mock_uuid.side_effect = ['session-id', 'msg-id']
        msg_id = "msg-id"
        other_msg_id = "other-msg-id"

        mock_ws = Mock()
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(other_msg_id, 'stream', {'text': 'Should be ignored\n'}),
            self._create_mock_message(msg_id, 'stream', {'text': 'Should be included\n'}),
            self._create_mock_message(msg_id, 'status', {'execution_state': 'idle'})
        ])
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)
        result = buffer.getvalue()

        # The result should not contain the ignored message
        assert 'Should be ignored' not in result
        assert 'Should be included' in result
        mock_ws.close.assert_called_once()

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    def test_ws_close_on_exception(self, mock_create_connection):
        mock_ws = Mock()
        mock_ws.recv.side_effect = Exception("Error during recv")
        mock_ws.close.side_effect = Exception("Error during close")  # Even if close fails
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        with pytest.raises(JupyterWSError):
            execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)

        # close should be attempted even if it raises
        mock_ws.close.assert_called_once()

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_keyboard_interrupt_sends_interrupt_request(self, mock_uuid, mock_create_connection):
        """Test that KeyboardInterrupt sends interrupt_request to remote kernel."""
        # Use fixed UUIDs for testing
        mock_uuid.side_effect = ['session-id', 'msg-id', 'interrupt-msg-id']

        mock_ws = Mock()
        # Simulate KeyboardInterrupt during recv
        mock_ws.recv.side_effect = KeyboardInterrupt("User interrupted")
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        with pytest.raises(KeyboardInterrupt):
            execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)

        # Verify that send was called twice: once for execute_request, once for interrupt_request
        assert mock_ws.send.call_count == 2

        # Check the second call was an interrupt_request
        second_call_arg = mock_ws.send.call_args_list[1][0][0]
        interrupt_msg = json.loads(second_call_arg)
        assert interrupt_msg['header']['msg_type'] == 'interrupt_request'
        assert interrupt_msg['header']['session'] == 'session-id'
        assert interrupt_msg['header']['msg_id'] == 'interrupt-msg-id'
        assert interrupt_msg['content'] == {}

        # Verify close was called
        mock_ws.close.assert_called_once()

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_keyboard_interrupt_during_execution(self, mock_uuid, mock_create_connection):
        """Test KeyboardInterrupt during code execution (after receiving some output)."""
        mock_uuid.side_effect = ['session-id', 'msg-id', 'interrupt-msg-id']
        msg_id = "msg-id"

        mock_ws = Mock()
        # Send some output, then raise KeyboardInterrupt
        mock_ws.recv = Mock(side_effect=[
            self._create_mock_message(msg_id, 'stream', {'text': 'Started execution\n'}),
            KeyboardInterrupt("User interrupted")
        ])
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        with pytest.raises(KeyboardInterrupt):
            execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)

        # Verify we got some output before interrupt
        assert 'Started execution\n' in buffer.getvalue()

        # Verify interrupt_request was sent
        assert mock_ws.send.call_count == 2
        second_call_arg = mock_ws.send.call_args_list[1][0][0]
        interrupt_msg = json.loads(second_call_arg)
        assert interrupt_msg['header']['msg_type'] == 'interrupt_request'

    @patch('jupyter_remote_exec.ws_client.websocket.create_connection')
    @patch('jupyter_remote_exec.ws_client.uuid.uuid4')
    def test_keyboard_interrupt_send_failure(self, mock_uuid, mock_create_connection):
        """Test that KeyboardInterrupt is still raised even if interrupt_request send fails."""
        mock_uuid.side_effect = ['session-id', 'msg-id', 'interrupt-msg-id']

        mock_ws = Mock()
        mock_ws.recv.side_effect = KeyboardInterrupt("User interrupted")
        # Make the second send (interrupt_request) fail
        mock_ws.send.side_effect = [None, Exception("Send failed")]
        mock_create_connection.return_value = mock_ws

        buffer = StringIO()
        # KeyboardInterrupt should still be raised even if interrupt send fails
        with pytest.raises(KeyboardInterrupt):
            execute_code_over_ws("localhost", 8888, "kernel-123", "token", "code", file=buffer)

        # Verify send was attempted twice
        assert mock_ws.send.call_count == 2
        mock_ws.close.assert_called_once()
