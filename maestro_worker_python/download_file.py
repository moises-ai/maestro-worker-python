from __future__ import annotations
import requests

import logging
import os
import socket
import tempfile
import threading
import time
from typing import Iterator, Optional

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from contextlib import contextmanager

from .response import ValidationError


# Bounds connecting, waiting for headers and each socket read.
_IDLE_TIMEOUT_SECONDS = 30
# A body that keeps trickling never trips the socket timeout, so without a
# floor a download hangs for as long as the server keeps sending. Each window
# is judged on its own: an average since the start lets a fast first stretch
# hide a trickle for minutes.
_STALL_WINDOW_SECONDS = 30
_MIN_BYTES_PER_WINDOW = 2 * 1024 * 1024
# A read returns only once its whole chunk has arrived, so bytes count toward a
# window late by up to one chunk: keep it well under the per-window floor.
_CHUNK_SIZE = 64 * 1024


class DownloadStalledError(RuntimeError):
    """An input download fell below the minimum transfer rate.

    Not retried here: a source that turns slow tends to stay slow, so retrying at once would hang again.
    """


def download_file(url: str, filename: str = None):
    logging.info(f"Downloading input: {url}")
    with requests.get(url, allow_redirects=True, timeout=_IDLE_TIMEOUT_SECONDS, stream=True) as response:
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ValidationError(f"Bad download input: {response.status_code}: {e}")

        file_name = filename if filename is not None else tempfile.mktemp()
        try:
            with open(file_name, 'wb') as file, _BodyWatchdog(response) as watchdog:
                for chunk in watchdog.iter_content():
                    file.write(chunk)
        except BaseException:
            if filename is None and os.path.exists(file_name):
                os.unlink(file_name)
            raise

    logging.info(f"Downloaded input to {file_name}")
    return file_name


class _BodyWatchdog:
    """Fails a response body once a window ends having brought fewer than ``_MIN_BYTES_PER_WINDOW``.

    Shutting the socket down is what unblocks a read waiting on the trickle.
    """

    def __init__(self, response: requests.Response):
        self._response = response
        self._sock = _body_socket(response)
        # Bytes the reads have returned: urllib3 leaves ``response.raw.tell()`` at 0 for a chunked body.
        self._received = 0
        self._fired = False
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._watch, name="download-watchdog", daemon=True)

    def __enter__(self) -> "_BodyWatchdog":
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._done.set()
        self._thread.join()

    def iter_content(self) -> Iterator[bytes]:
        chunks = self._response.iter_content(_CHUNK_SIZE)
        while True:
            try:
                chunk = next(chunks)
            except StopIteration:
                break
            except Exception:
                if self._fired:
                    raise self._stalled() from None
                raise
            # Checked per read too, so the floor holds even when the socket could not be shut down,
            # and a shut-down socket that reads as a clean end of body still fails.
            if self._fired:
                raise self._stalled()
            self._received += len(chunk)
            yield chunk
        if self._fired:
            raise self._stalled()

    def _stalled(self) -> DownloadStalledError:
        return DownloadStalledError(
            f"Input download fell below {_MIN_BYTES_PER_WINDOW} bytes per {_STALL_WINDOW_SECONDS}s "
            f"after {self._received} bytes"
        )

    def _watch(self) -> None:
        window_started, window_start_received = time.monotonic(), 0
        # Polling a quarter window catches a stall at most a quarter window late.
        while not self._done.wait(_STALL_WINDOW_SECONDS / 4):
            now = time.monotonic()
            if now - window_started < _STALL_WINDOW_SECONDS:
                continue
            received = self._received
            if received - window_start_received >= _MIN_BYTES_PER_WINDOW:
                window_started, window_start_received = now, received
                continue
            self._fired = True
            if self._sock is not None:
                try:
                    # SSLSocket.shutdown would tear down TLS state the reading thread is using.
                    socket.socket.shutdown(self._sock, socket.SHUT_RDWR)
                except OSError:
                    pass
            return


def _body_socket(response: requests.Response) -> Optional[socket.socket]:
    """The socket the body is read from.

    Not ``response.raw.connection.sock``: http.client clears that when the server
    will close the connection, while the body still reads from this one.
    """
    body_stream = getattr(getattr(response.raw, "_fp", None), "fp", None)
    return getattr(getattr(body_stream, "raw", None), "_sock", None)


@contextmanager
def download_files_manager(*urls: str) -> None | str | list[str]:
    try:
        thread_list = []
        list_objects = []
        for url in urls:
            filename = tempfile.NamedTemporaryFile()
            logging.info("Downloading file from url -> %s, filename -> %s", url, filename.name)
            with ThreadPoolExecutor(max_workers=20) as exe:
                thread_list.append(exe.submit(download_file, url, filename.name))
            list_objects.append(filename)
        for thread in as_completed(thread_list):
            path = thread.result()
            logging.info("File downloaded to: %s", path)
        downloaded_files = [obj.name for obj in list_objects]
        if len(downloaded_files) == 0:
            yield None
        elif len(downloaded_files) == 1:
            yield downloaded_files[0]
        else:
            yield downloaded_files
    finally:
        for obj in list_objects:
            obj.close()
