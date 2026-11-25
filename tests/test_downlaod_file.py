import contextlib
import os
import socket
import tempfile
import threading
import time
from typing import Iterator

import pytest
from maestro_worker_python import download_file as download_module
from maestro_worker_python.download_file import DownloadStalledError, download_file, download_files_manager
from maestro_worker_python.response import ValidationError


def test_download_file(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    file_name = download_file(url)
    with open(file_name) as f:
        assert f.read() == "hello"


def test_bad_response_should_raise_validation_error(httpserver):
    httpserver.expect_request("/bad_url").respond_with_data("", status=404)
    bad_url = httpserver.url_for("/bad_url")

    with pytest.raises(ValidationError) as excinfo:
        download_file(bad_url)

    assert "Bad download input" in str(excinfo.value)


def test_download_files_manager(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    files_content = []
    with download_files_manager(url, url) as downloaded_files:
        for file in downloaded_files:
            with open(file) as f:
                files_content.append(f.read() == "hello")
    assert all(files_content) == True


def test_download_files_manager_delete(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    files_path_exists = []
    with download_files_manager(url, url) as downloaded_files:
        files_path = downloaded_files
    for path in files_path:
        files_path_exists.append(os.path.exists(path))
    assert all(files_path_exists) == False


@pytest.fixture
def short_window(monkeypatch):
    """Scales the floor down so a test runs in seconds; the socket timeout outlasts the test."""
    monkeypatch.setattr(download_module, "_CHUNK_SIZE", 100)
    monkeypatch.setattr(download_module, "_STALL_WINDOW_SECONDS", 1)
    monkeypatch.setattr(download_module, "_MIN_BYTES_PER_WINDOW", 1000)
    monkeypatch.setattr(download_module, "_IDLE_TIMEOUT_SECONDS", 10)


# Each failing case's server keeps going well past this.
FAIL_WITHIN_SECONDS = 4


def _serve_once(handler) -> str:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    def run():
        with listener, contextlib.suppress(OSError):
            conn, _ = listener.accept()
            with conn:
                conn.recv(65536)
                handler(conn)

    threading.Thread(target=run, daemon=True).start()
    return f"http://127.0.0.1:{listener.getsockname()[1]}/input"


def _respond(body: Iterator[bytes], *, chunked: bool, length: int = 10**9) -> str:
    framing = b"Transfer-Encoding: chunked" if chunked else b"Content-Length: %d" % length

    def handler(conn):
        conn.sendall(b"HTTP/1.1 200 OK\r\n" + framing + b"\r\n\r\n")
        for piece in body:
            conn.sendall(b"%x\r\n%s\r\n" % (len(piece), piece) if chunked else piece)
        if chunked:
            conn.sendall(b"0\r\n\r\n")

    return _serve_once(handler)


def _paced(piece: bytes, *, every: float, count: int) -> Iterator[bytes]:
    for _ in range(count):
        yield piece
        time.sleep(every)


def _trickle_after_a_fast_start() -> Iterator[bytes]:
    yield b"x" * 5000
    yield from _paced(b"x" * 10, every=0.1, count=60)


def _silence() -> Iterator[bytes]:
    time.sleep(2 * FAIL_WITHIN_SECONDS)
    yield from ()


def _assert_fails_as_stalled(url: str) -> None:
    started = time.monotonic()
    with pytest.raises(DownloadStalledError):
        download_file(url)
    assert time.monotonic() - started < FAIL_WITHIN_SECONDS


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_download_that_trickles_after_a_fast_start_fails(short_window, chunked):
    _assert_fails_as_stalled(_respond(_trickle_after_a_fast_start(), chunked=chunked))


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_download_above_the_floor_completes_across_windows(short_window, chunked):
    pieces = [b"y" * 500] * 25  # 5000 bytes/s for 2.5 windows
    url = _respond(_paced(pieces[0], every=0.1, count=len(pieces)), chunked=chunked, length=len(b"".join(pieces)))

    file_name = download_file(url)
    with open(file_name, "rb") as f:
        assert f.read() == b"".join(pieces)


def test_download_that_sends_no_body_bytes_fails(short_window):
    _assert_fails_as_stalled(_respond(_silence(), chunked=False, length=100))


def test_trickle_fails_even_when_its_socket_cannot_be_found(short_window, monkeypatch):
    monkeypatch.setattr(download_module, "_body_socket", lambda response: None)
    _assert_fails_as_stalled(_respond(_trickle_after_a_fast_start(), chunked=False))


def test_stalled_download_leaves_no_temporary_file(short_window, monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    _assert_fails_as_stalled(_respond(_trickle_after_a_fast_start(), chunked=False))
    assert list(tmp_path.iterdir()) == []
