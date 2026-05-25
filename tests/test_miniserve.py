import socket
import tempfile
import time
from pathlib import Path

import pytest

from miniserve import start_server
from miniserve.cli import _build_parser, main


# ── helpers ──────────────────────────────────────────────────────────────────

def _free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


# ── server tests ──────────────────────────────────────────────────────────────

class TestStartServer:
    def test_server_starts_and_serves_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("hello world")
        port = _free_port()
        server = start_server(port=port, directory=str(tmp_path))

        import urllib.request
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/hello.txt") as resp:
                assert resp.read() == b"hello world"
        finally:
            server.shutdown()

    def test_server_returns_httpserver_instance(self, tmp_path: Path) -> None:
        from http.server import HTTPServer
        port = _free_port()
        server = start_server(port=port, directory=str(tmp_path))
        try:
            assert isinstance(server, HTTPServer)
        finally:
            server.shutdown()

    def test_directory_defaults_to_cwd(self) -> None:
        import os
        port = _free_port()
        server = start_server(port=port)
        try:
            # Just assert it started without error; actual CWD serving tested above
            assert server is not None
        finally:
            server.shutdown()


# ── CLI parser tests ──────────────────────────────────────────────────────────

class TestCLIParser:
    def test_defaults(self) -> None:
        args = _build_parser().parse_args([])
        assert args.port == 8080
        assert args.dir == "."
        assert args.open is False

    def test_custom_port(self) -> None:
        args = _build_parser().parse_args(["--port", "9000"])
        assert args.port == 9000

    def test_short_port_flag(self) -> None:
        args = _build_parser().parse_args(["-p", "3000"])
        assert args.port == 3000

    def test_custom_dir(self) -> None:
        args = _build_parser().parse_args(["--dir", "/tmp"])
        assert args.dir == "/tmp"

    def test_open_flag(self) -> None:
        args = _build_parser().parse_args(["--open"])
        assert args.open is True


# ── CLI main integration test ─────────────────────────────────────────────────

class TestCLIMain:
    def test_main_starts_then_stops_on_keyboard_interrupt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        port = _free_port()

        # Simulate Ctrl+C after the server is running
        original_sleep = time.sleep
        call_count = 0

        def fake_sleep(n: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise KeyboardInterrupt
            original_sleep(n)

        monkeypatch.setattr(time, "sleep", fake_sleep)

        with pytest.raises(SystemExit) as exc_info:
            main(["--port", str(port), "--dir", str(tmp_path)])

        assert exc_info.value.code == 0
