
import threading
from dataclasses import dataclass
from typing import List
import requests
import logging
from subprocess import check_call
logging.basicConfig(level=logging.INFO)


@dataclass
class FileToConvert:
    input_file_path: str
    output_file_path: str
    file_format: str
    max_duration: int = 1200


def convert_files(convert_files: List[FileToConvert]):
    logging.info(f"Converting {len(convert_files)} files")
    did_raise_exception = threading.Event()
    threads_conversion = []

    for convert_file in convert_files:
        target_function = _convert_to_m4a if convert_file.file_format == "m4a" else _convert_to_wav
        t = threading.Thread(target=target_function, args=(
            convert_file.input_file_path, convert_file.output_file_path, convert_file.max_duration, did_raise_exception))
        threads_conversion.append(t)
        t.start()

    for t in threads_conversion:
        t.join()

    if did_raise_exception.is_set():
        raise Exception("Error during file conversion")
    logging.info(f"Finished converting {len(convert_files)} files")


def _convert_to_wav(input_file_path, output_file_path, max_duration, did_raise_exception):
    try:
        check_call(
            f"ffmpeg -y -hide_banner -loglevel error -t {max_duration} -i {input_file_path} -ar 44100 {output_file_path}", shell=True)
    except Exception as ve:
        logging.exception(ve)
        did_raise_exception.set()
        raise ve


def _convert_to_m4a(input_file_path, output_file_path, max_duration, did_raise_exception):
    try:
        check_call(
            f"ffmpeg -y -hide_banner -loglevel error -t {max_duration} -i {input_file_path} -c:a aac -b:a 192k -ar 44100 -movflags +faststart {output_file_path}", shell=True)
        return output_file_path
    except Exception as ve:
        logging.exception(ve)
        did_raise_exception.set()
        raise ve
