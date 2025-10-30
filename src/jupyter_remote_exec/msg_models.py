"""
Message model (factory) utilities for Jupyter kernel WebSocket protocol.

This module centralizes construction of protocol-compliant messages so that
callers (like ws_client) don't hand-craft dicts inline.
"""
from typing import Dict, Any


def build_execute_request(code: str, session_id: str, msg_id: str,
                          username: str = 'remote', version: str = '5.3') -> Dict[str, Any]:
    """
    Build a Jupyter messaging protocol 'execute_request' message payload.

    This mirrors the minimal set used by the project. If you need to extend
    the protocol (e.g., add metadata fields), do it here to keep call sites clean.
    """
    return {
        'channel': 'shell',
        'header': {
            'msg_id': msg_id,
            'msg_type': 'execute_request',
            'session': session_id,
            'username': username,
            'version': version,
            'date': ''  # left blank as before; Jupyter does not require it here for our usage
        },
        'parent_header': {},
        'metadata': {},
        'content': {
            'code': code,
            'silent': False,
            'store_history': True,
            'user_expressions': {},
            'allow_stdin': False
        }
    }


def build_interrupt_request(session_id: str, msg_id: str,
                            username: str = 'remote', version: str = '5.3') -> Dict[str, Any]:
    """
    Build a Jupyter messaging protocol 'interrupt_request' message payload.

    This sends a kernel interrupt signal to stop the currently executing code.
    """
    return {
        'channel': 'shell',
        'header': {
            'msg_id': msg_id,
            'msg_type': 'interrupt_request',
            'session': session_id,
            'username': username,
            'version': version,
            'date': ''
        },
        'parent_header': {},
        'metadata': {},
        'content': {}
    }
