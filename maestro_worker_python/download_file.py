import logging
import tempfile

from urllib.parse import urlparse
from urllib.request import urlretrieve
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from contextlib import contextmanager
from typing import List
from dataclasses import dataclass

def download_file(url: str):
    logging.info(f"Downloading input: {urlparse(url).path}")
    file_name, _ = urlretrieve(url)
    logging.info(f"Downloaded input")
    return file_name

@contextmanager
def download_files_manager(url_list: List[str]):
    try:
        thread_list = []
        list_objects = []
        for url in url_list:
            filename = tempfile.NamedTemporaryFile()
            logging.info("Downloading file from url -> %s, filename -> %s", url, filename.name)
            with ThreadPoolExecutor(max_workers=20) as exe:
                thread_list.append(exe.submit(urlretrieve, url, filename.name))
            list_objects.append(filename)
        for thread in as_completed(thread_list):
            path, _ = thread.result()
            logging.info("File downloaded to: %s", path)
        yield [obj.name for obj in list_objects]
    finally:
        for obj in list_objects:
            obj.close()