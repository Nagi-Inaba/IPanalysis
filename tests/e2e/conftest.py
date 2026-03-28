# -*- coding: utf-8 -*-
"""Playwright E2E テスト用フィクスチャ — Streamlit サーバーの起動・停止。"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2]
APP_FILE = APP_DIR / "app.py"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="function")
def context(browser):
    """テストごとに新しいブラウザコンテキストを作成（Cookie / セッション分離）。"""
    ctx = browser.new_context()
    yield ctx
    ctx.close()


@pytest.fixture(scope="session")
def app_url():
    """Streamlit アプリをサブプロセスで起動し、テスト終了後に停止する。"""
    port = _find_free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "streamlit", "run",
            str(APP_FILE),
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(APP_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if not _wait_for_server(port):
        proc.kill()
        out, err = proc.communicate(timeout=5)
        pytest.fail(
            f"Streamlit が {port} で起動しませんでした。\n"
            f"stdout: {out.decode(errors='replace')[:500]}\n"
            f"stderr: {err.decode(errors='replace')[:500]}"
        )
    yield f"http://localhost:{port}"
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
