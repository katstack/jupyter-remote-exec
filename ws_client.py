"""
WebSocket client utilities for interacting with Jupyter kernel channels.

This module encapsulates the low-level websocket connection and message flow for
sending an 'execute_request' and collecting textual stdout output.
"""
from typing import Optional, List, Union
import json
import uuid
import ssl
import websocket
from msg_models import build_execute_request

DEFAULT_WS_TIMEOUT = 30  # seconds

class JupyterWSError(Exception):
    pass


def execute_code_over_ws(host: str, port: int, kernel_id: str, token: Optional[str], code: str,
                          timeout: Optional[float] = None,
                          https: bool = False,
                          verify: Optional[Union[bool, str]] = None) -> str:
    """
    Connect to Jupyter kernel channels via WebSocket, send execute_request, and
    return concatenated stdout text output.

    Args:
        host, port, kernel_id: connection targets
        token: auth token; if None, connects without token (only if server allows)
        timeout: socket timeout in seconds
        https: if True, use wss:// (TLS) instead of ws://
        verify: TLS verification behavior (only used when https=True)
            - True: default system CA verification
            - False: disable certificate verification (dev only)
            - str: path to CA bundle file
    """
    scheme = "wss" if https else "ws"
    token_q = f"?token={token}" if token else ""
    ws_url = f"{scheme}://{host}:{port}/api/kernels/{kernel_id}/channels{token_q}"

    sslopt = None
    if https:
        sslopt = {}
        if verify is False:
            sslopt["cert_reqs"] = ssl.CERT_NONE
        elif verify is True or verify is None:
            # default verification; leave sslopt empty to use defaults
            pass
        elif isinstance(verify, str):
            sslopt["cert_reqs"] = ssl.CERT_REQUIRED
            sslopt["ca_certs"] = verify

    try:
        if sslopt is not None:
            ws = websocket.create_connection(ws_url, timeout=timeout or DEFAULT_WS_TIMEOUT, sslopt=sslopt)
        else:
            ws = websocket.create_connection(ws_url, timeout=timeout or DEFAULT_WS_TIMEOUT)
    except Exception as e:
        raise JupyterWSError(f"Failed to connect WS: {e}") from e

    session_id = str(uuid.uuid4())
    msg_id = str(uuid.uuid4())

    msg = build_execute_request(code=code, session_id=session_id, msg_id=msg_id, username='remote', version='5.3')

    outputs: List[str] = []
    try:
        ws.send(json.dumps(msg))
        while True:
            raw = ws.recv()
            result = json.loads(raw)
            parent_msg_id = result.get('parent_header', {}).get('msg_id', '')
            if parent_msg_id != msg_id:
                continue
            mtype = result.get('msg_type')
            if mtype == 'stream':
                outputs.append(result.get('content', {}).get('text', ''))
            if mtype == 'status' and result.get('content', {}).get('execution_state') == 'idle':
                break
    except Exception as e:
        raise JupyterWSError(f"WS communication error: {e}") from e
    finally:
        try:
            ws.close()
        except Exception:
            pass

    return ''.join(outputs)
