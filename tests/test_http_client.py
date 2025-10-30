"""Tests for HTTP client utilities."""
import pytest
from unittest.mock import Mock, patch
import requests
from jupyter_remote_exec.http_client import create_kernel, JupyterHTTPError, DEFAULT_TIMEOUT


class TestCreateKernel:
    """Test the create_kernel function."""

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_successful_kernel_creation(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-123"}
        mock_post.return_value = mock_response

        kernel_id = create_kernel("localhost", 8888, "test-token")

        assert kernel_id == "kernel-123"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['headers']['Authorization'] == 'Token test-token'
        assert call_kwargs['timeout'] == DEFAULT_TIMEOUT

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_without_token(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-456"}
        mock_post.return_value = mock_response

        kernel_id = create_kernel("localhost", 8888, None)

        assert kernel_id == "kernel-456"
        call_kwargs = mock_post.call_args[1]
        assert 'Authorization' not in call_kwargs['headers']

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_with_https(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-789"}
        mock_post.return_value = mock_response

        kernel_id = create_kernel("localhost", 8888, "token", https=True)

        assert kernel_id == "kernel-789"
        url = mock_post.call_args[0][0]
        assert url.startswith("https://")

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_with_http(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-000"}
        mock_post.return_value = mock_response

        kernel_id = create_kernel("localhost", 8888, "token", https=False)

        url = mock_post.call_args[0][0]
        assert url.startswith("http://")
        assert not url.startswith("https://")

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_with_verify_false(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-verify"}
        mock_post.return_value = mock_response

        kernel_id = create_kernel("localhost", 8888, "token", https=True, verify=False)

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['verify'] is False

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_with_verify_path(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-cert"}
        mock_post.return_value = mock_response

        cert_path = "/path/to/cert.pem"
        kernel_id = create_kernel("localhost", 8888, "token", https=True, verify=cert_path)

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['verify'] == cert_path

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_with_custom_timeout(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-timeout"}
        mock_post.return_value = mock_response

        create_kernel("localhost", 8888, "token", timeout=30.0)

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['timeout'] == 30.0

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_non_201_status(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(JupyterHTTPError) as exc_info:
            create_kernel("localhost", 8888, "token")

        assert "Failed to create kernel: 500" in str(exc_info.value)

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_invalid_json(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        with pytest.raises(JupyterHTTPError) as exc_info:
            create_kernel("localhost", 8888, "token")

        assert "Invalid JSON response" in str(exc_info.value)

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_missing_id(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {}  # Missing 'id' key
        mock_post.return_value = mock_response

        with pytest.raises(JupyterHTTPError) as exc_info:
            create_kernel("localhost", 8888, "token")

        assert "Invalid JSON response" in str(exc_info.value)

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_kernel_creation_connection_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Connection failed")

        with pytest.raises(JupyterHTTPError) as exc_info:
            create_kernel("localhost", 8888, "token")

        assert "HTTP request failed" in str(exc_info.value)

    @patch('jupyter_remote_exec.http_client.requests.post')
    def test_url_construction(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "kernel-url"}
        mock_post.return_value = mock_response

        create_kernel("example.com", 9999, "token", https=True)

        url = mock_post.call_args[0][0]
        assert url == "https://example.com:9999/api/kernels"
