from __future__ import annotations

import logging
import tempfile
import time

from contextlib import contextmanager
from urllib.request import urlretrieve
from typing import Dict
from convert_files import FileToConvert, convert_files


@contextmanager
def prepare_audios(dict_urls: Dict[str, str], max_duration: float):
    dst_dict = {}
    for key in dict_urls.keys():
        dst_dict[key] = {}
        dst_dict[key]['dst_file'] = tempfile.NamedTemporaryFile()
        dst_dict[key]['dst_proc_file'] = tempfile.NamedTemporaryFile(
            suffix=".wav")
    try:
        for key in dst_dict.keys():
            logging.info(
                "Downloading file from input -> %s, url -> %s, filename -> %s",
                key, dict_urls[key], dst_dict[key]['dst_file'].name)
            urlretrieve(dict_urls[key], dst_dict[key]['dst_file'].name)
            logging.info("Downloaded file to %s",
                         dst_dict[key]['dst_file'].name)
            logging.info("Shortening file to %.2f seconds.", max_duration)
            convert_files([
                FileToConvert(
                    input_file_path=dst_dict[key]['dst_file'].name,
                    output_file_path=dst_dict[key]['dst_proc_file'].name,
                    file_format="wav",
                    max_duration=max_duration,
                )
            ])
            logging.info("Saved shortened file to %s.",
                         dst_dict[key]['dst_proc_file'].name)
        yield dst_dict
    finally:
        for key in dst_dict.keys():
            dst_dict[key]['dst_file'].close()
            dst_dict[key]['dst_proc_file'].close()


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