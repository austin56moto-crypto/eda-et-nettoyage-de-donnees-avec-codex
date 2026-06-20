"""Launch the local Flask dashboard for the grant data quality project."""

from __future__ import annotations

import os
import socket
from pathlib import Path

from dashboard_site.app import app


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PORT_SCAN_LIMIT = 25


def port_is_available(host: str, port: int) -> bool:
    """Return whether a TCP port is currently available on the given host."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def choose_port(host: str, preferred_port: int) -> int:
    """Choose a usable port, falling back when the preferred one is occupied."""

    requested_port = os.getenv("PORT")
    if requested_port:
        return int(requested_port)

    for port in range(preferred_port, preferred_port + PORT_SCAN_LIMIT):
        if port_is_available(host, port):
            return port

    raise RuntimeError(
        f"No available port found between {preferred_port} and "
        f"{preferred_port + PORT_SCAN_LIMIT - 1}."
    )


if __name__ == "__main__":
    host = os.getenv("HOST", DEFAULT_HOST)
    port = choose_port(host, DEFAULT_PORT)
    url = f"http://{host}:{port}"
    url_file = os.getenv("DASHBOARD_URL_FILE")
    if url_file:
        Path(url_file).write_text(url, encoding="utf-8")
    print(f"Dashboard running at {url}")
    app.run(host=host, port=port, debug=False)
