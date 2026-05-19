from __future__ import annotations

from server import build_server


def test_build_server_returns_mcp_instance():
    server = build_server()

    assert server.name == "smart-scheduler-mcp"
