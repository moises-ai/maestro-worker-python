
import threading
from dataclasses import dataclass
from typing import List
import requests
import logging
logging.basicConfig(level=logging.INFO)


@dataclass
class UploadFile:
    file_path: str
    file_type: str
    signed_url: str


def upload_files(upload_files: List[UploadFile]):
    logging.info(f"Uploading {len(upload_files)} files")
    threads_upload = []
    did_raise_exception = threading.Event()
    for file_ in upload_files:
        t = threading.Thread(target=_upload, args=(
            file_, did_raise_exception,))
        threads_upload.append(t)
        t.start()
    
    for t in threads_upload:
        t.join()

    if did_raise_exception.is_set():
        raise Exception("Error during file Upload")

def _upload(upload_file: UploadFile, did_raise_exception):
    logging.info(f"Uploading:{upload_file.file_path}")
    try:
        with open(upload_file.file_path, 'rb') as data:
            response = requests.put(upload_file.signed_url, data=data, headers={
                "Content-Type": upload_file.file_type})
            response.raise_for_status()
            logging.info(f"Uploaded {upload_file.file_path}")
    except Exception as e:
        did_raise_exception.set()
        logging.exception(e)
        raise e