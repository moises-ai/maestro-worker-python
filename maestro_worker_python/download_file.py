from __future__ import annotations

import os
import logging
import tempfile
import requests

from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from contextlib import contextmanager


def download_file(url: str):
    logging.info(f"Downloading input: {urlparse(url).path}")
    response = requests.get(url, allow_redirects=True)

    if response.status_code == 200:
        file_name = urlparse(url).path.split('/')[-1] or 'downloaded_file'
        file_name = os.path.join(tempfile.gettempdir(), file_name)
        with open(file_name, 'wb') as file:
            file.write(response.content)

        logging.info(f"Downloaded input to {file_name}")
        return file_name
    else:
        logging.error(f"Failed to download file: HTTP {response.status_code}")
        return None



@contextmanager
def download_files_manager(*urls: str):
    try:
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_url = {executor.submit(download_file, url): url for url in urls}

            downloaded_files = []
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    file_name = future.result()
                    if file_name:
                        downloaded_files.append(file_name)
                        logging.info(f"File downloaded from {url} to {file_name}")
                    else:
                        logging.error(f"Failed to download file from {url}")
                except Exception as exc:
                    logging.error(f"Error downloading file from {url}: {exc}")

            if len(downloaded_files) == 0:
                yield None
            elif len(downloaded_files) == 1:
                yield downloaded_files[0]
            else:
                yield downloaded_files

    finally:
        for file_name in downloaded_files:
            try:
                os.remove(file_name)
                logging.info(f"Deleted temporary file {file_name}")
            except Exception as exc:
                logging.warning(f"Could not delete temporary file {file_name}: {exc}")
