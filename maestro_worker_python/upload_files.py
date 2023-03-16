from __future__ import annotations

import json
import logging
import tempfile
import threading
import concurrent.futures
from dataclasses import dataclass
from os.path import join
from typing import List, Any

import requests


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
        with open(upload_file.file_path, "rb") as data:
            response = requests.put(upload_file.signed_url, data=data, headers={"Content-Type": upload_file.file_type})
            response.raise_for_status()
            logging.info(f"Uploaded {upload_file.file_path}")
    except Exception as e:
        did_raise_exception.set()
        logging.exception(e)
        raise e


@dataclass
class UploadJsonData:
    data: Any
    signed_url: str


def upload_json_data(upload_data: list[UploadJsonData]):
    files_to_upload = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, upload in enumerate(upload_data):
            with open(join(tmp_dir, f"{i}.json"), "w") as tmp_file:
                json.dump(upload.data, tmp_file)
                tmp_file.flush()
                files_to_upload.append(
                    UploadFile(file_path=tmp_file.name, signed_url=upload.signed_url, file_type="application/json")
                )
        upload_files(files_to_upload)


class AsyncUploader:
    """
    Allows to upload files and json data asynchronously.

    Usage:

    with AsyncUploader() as uploader:
        json_data = process_audio(...)
        uploader.upload_json(json_data, signed_url)
        # this runs without waiting for the upload to finish
        other_results = process_other(...)

    # this will wait for all uploads to finish
    do_more_things(...)
    """

    def __init__(self, max_workers: int | None = None):
        self._max_workers = max_workers
        self._exectuor = None
        self._futures = []

    def __enter__(self):
        self._exectuor = concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._exectuor.shutdown()
        for future in self._futures:
            if future.exception():
                raise future.exception()

    def upload_file(self, file_path: str, file_type: str, signed_url: str | None) -> concurrent.futures.Future:
        self._futures.append(self._exectuor.submit(upload_files, [UploadFile(file_path, file_type, signed_url)]))
        return self._futures[-1]

    def upload_json(self, data: Any, signed_url: str | None) -> concurrent.futures.Future:
        self._futures.append(self._exectuor.submit(upload_json_data, [UploadJsonData(data, signed_url)]))
        return self._futures[-1]
