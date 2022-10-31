
import logging
import urllib.request
logging.basicConfig(level=logging.INFO)

def download_file(signed_url: str):
    logging.info(f"Downloading input")
    file_name, headers = urllib.request.urlretrieve(signed_url)
    logging.info(f"Downloaded input")
    return file_name