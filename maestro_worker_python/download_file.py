
import logging
import urllib.request
from urllib.parse import urlparse


def download_file(signed_url: str):
    logging.info(f"Downloading input: {urlparse(signed_url).path}")
    file_name, headers = urllib.request.urlretrieve(signed_url)
    logging.info(f"Downloaded input")
    return file_name
