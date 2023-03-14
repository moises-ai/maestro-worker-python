from __future__ import annotations

import logging
import tempfile

from urllib.parse import urlparse
from urllib.request import urlretrieve
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from contextlib import contextmanager


def download_file(url: str):
    logging.info(f"Downloading input: {urlparse(url).path}")
    file_name, _ = urlretrieve(url)
    logging.info(f"Downloaded input")
    return file_name


@contextmanager
def download_files_manager(*urls: str) -> None | str | list[str]:
    try:
        thread_list = []
        list_objects = []
        for url in urls:
            filename = tempfile.NamedTemporaryFile()
            logging.info("Downloading file from url -> %s, filename -> %s", url, filename.name)
            with ThreadPoolExecutor(max_workers=20) as exe:
                thread_list.append(exe.submit(urlretrieve, url, filename.name))
            list_objects.append(filename)
        for thread in as_completed(thread_list):
            path, _ = thread.result()
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
