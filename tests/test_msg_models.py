"""Tests for message model utilities."""
import pytest
from jupyter_remote_exec.msg_models import build_execute_request


class TestBuildExecuteRequest:
    """Test the build_execute_request function."""

    def test_basic_execute_request(self):
        code = "print('hello')"
        session_id = "test-session"
        msg_id = "test-msg-id"

        msg = build_execute_request(code, session_id, msg_id)

        assert msg['channel'] == 'shell'
        assert msg['header']['msg_id'] == msg_id
        assert msg['header']['msg_type'] == 'execute_request'
        assert msg['header']['session'] == session_id
        assert msg['header']['username'] == 'remote'
        assert msg['header']['version'] == '5.3'
        assert msg['content']['code'] == code
        assert msg['content']['silent'] is False
        assert msg['content']['store_history'] is True
        assert msg['content']['allow_stdin'] is False

    def test_custom_username_version(self):
        msg = build_execute_request(
            code="x = 1",
            session_id="sess1",
            msg_id="msg1",
            username="testuser",
            version="5.4"
        )

        assert msg['header']['username'] == 'testuser'
        assert msg['header']['version'] == '5.4'

    def test_message_structure(self):
        msg = build_execute_request("test", "sess", "msgid")

        # Check all required top-level keys
        assert 'channel' in msg
        assert 'header' in msg
        assert 'parent_header' in msg
        assert 'metadata' in msg
        assert 'content' in msg

        # Check header structure
        header = msg['header']
        assert 'msg_id' in header
        assert 'msg_type' in header
        assert 'session' in header
        assert 'username' in header
        assert 'version' in header
        assert 'date' in header

        # Check content structure
        content = msg['content']
        assert 'code' in content
        assert 'silent' in content
        assert 'store_history' in content
        assert 'user_expressions' in content
        assert 'allow_stdin' in content

    def test_empty_code(self):
        msg = build_execute_request("", "sess", "msgid")
        assert msg['content']['code'] == ""

    def test_multiline_code(self):
        code = """
def foo():
    return 42
print(foo())
"""
        msg = build_execute_request(code, "sess", "msgid")
        assert msg['content']['code'] == code
