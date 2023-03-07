from __future__ import annotations

import logging
import tempfile
import time
from contextlib import contextmanager
from urllib.request import urlretrieve

from convert_files import FileToConvert, convert_files


@contextmanager
def prepare_file(url: str, max_duration: float):
    dst_file = tempfile.NamedTemporaryFile()
    dst_proc_file = tempfile.NamedTemporaryFile(suffix=".wav")
    try:
        logging.info("Downloading file from %s to %s", url, dst_file.name)
        urlretrieve(url, dst_file.name)
        logging.info("Downloaded file to %s", dst_file.name)

        logging.info("Shortening file to %.2f seconds.", max_duration)
        convert_files(
            [
                FileToConvert(
                    input_file_path=dst_file.name,
                    output_file_path=dst_proc_file.name,
                    file_format="wav",
                    max_duration=max_duration,
                )
            ]
        )
        logging.info("Saved shortened file to %s.", dst_proc_file.name)

        yield dst_proc_file.name
    finally:
        dst_file.close()
        dst_proc_file.close()


class Timer:
    def __init__(self):
        self._starts = {}
        self._stops = {}

    def start(self, name: str):
        self._starts[name] = time.perf_counter()
        if name in self._stops:
            del self._stops[name]

    def stop(self, name: str):
        if name not in self._starts:
            raise ValueError(f"Timer {name} not started, can't be stopped.")
        self._stops[name] = time.perf_counter()

    def duration(self, name: str) -> float:
        if name not in self._starts:
            raise ValueError(f"Timer {name} not started!")

        return self._stops.get(name, time.perf_counter()) - self._starts[name]

    def duration_dict(self) -> dict[str, float]:
        return {name: self.duration(name) for name in self._starts}