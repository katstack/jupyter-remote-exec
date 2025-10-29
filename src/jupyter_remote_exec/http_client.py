"""
HTTP client utilities for interacting with Jupyter Server REST API.

This module encapsulates all direct 'requests' usages from the main script.
"""
from typing import Optional, Union
import requests

DEFAULT_TIMEOUT = 10  # seconds

class JupyterHTTPError(Exception):
    pass


def create_kernel(host: str, port: int, token: Optional[str],
                  timeout: Optional[float] = None,
                  https: bool = False,
                  verify: Optional[Union[bool, str]] = None) -> str:
    """
    Create a new kernel via Jupyter Server API and return the kernel id.

    Args:
        host: Jupyter server host (without scheme)
        port: Jupyter server port
        token: Jupyter auth token (optional; if None, no Authorization header)
        timeout: request timeout in seconds
        https: if True, use HTTPS instead of HTTP
        verify: TLS certificate verification behavior (only used when https=True)
            - True (default requests behavior): verify against system CAs
            - False: do not verify (useful for self-signed certs in dev)
            - str: path to a CA bundle file

    Raises JupyterHTTPError on failures.
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Token {token}"
    scheme = "https" if https else "http"
    url = f"{scheme}://{host}:{port}/api/kernels"

    request_kwargs = {"headers": headers, "timeout": timeout or DEFAULT_TIMEOUT}
    if https and verify is not None:
        request_kwargs["verify"] = verify

    try:
        resp = requests.post(url, **request_kwargs)
    except Exception as e:
        raise JupyterHTTPError(f"HTTP request failed: {e}") from e

    if resp.status_code == 201:
        try:
            data = resp.json()
            return data["id"]
        except Exception as e:
            raise JupyterHTTPError(f"Invalid JSON response for kernel creation: {e}") from e
    else:
        raise JupyterHTTPError(
            f"Failed to create kernel: {resp.status_code} - {resp.text[:2000]}"
        )
