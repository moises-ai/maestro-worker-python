from __future__ import annotations
import requests

import logging
import tempfile

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from contextlib import contextmanager

from .response import ValidationError


def download_file(url: str, filename: str = None):
    logging.info(f"Downloading input: {url}")
    response = requests.get(url, allow_redirects=True)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise ValidationError(f"Bad download input: {response.status_code}: {e}")

    file_name = filename if filename is not None else tempfile.mktemp()
    with open(file_name, 'wb') as file:
        file.write(response.content)

    logging.info(f"Downloaded input to {file_name}")
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
