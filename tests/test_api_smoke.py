#!/usr/bin/env python3
"""Smoke tests for FastAPI endpoints."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from api.main import app


def test_status_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert "mode" in payload
    assert "tick_rate" in payload
    assert "memory" in payload


def test_mcp_servers_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/mcp/servers")
    assert response.status_code == 200
    payload = response.json()
    assert "servers" in payload


def test_memory_bullets_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/memory/bullets?hemisphere=shared&limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert "bullets" in payload


def test_memory_stats_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/memory/stats")
    assert response.status_code == 200
    payload = response.json()
    assert "collections" in payload
    assert "status" in payload


def main() -> int:
    test_status_endpoint()
    test_mcp_servers_endpoint()
    test_memory_bullets_endpoint()
    test_memory_stats_endpoint()
    print("API smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
