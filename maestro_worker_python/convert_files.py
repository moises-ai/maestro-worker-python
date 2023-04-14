from __future__ import annotations

import tempfile
import logging
import subprocess
import concurrent.futures

from dataclasses import dataclass
from typing import List
from .response import ValidationError
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class FileConversionError(Exception):
    def __init__(self, message):
        self.message = message


@dataclass
class FileToConvert:
    input_file_path: str
    file_format: str
    output_file_path: str = None
    max_duration: int = 1200


def convert_files(convert_files: List[FileToConvert]):
    logger.info(f"Converting {len(convert_files)} files")

    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for convert_file in convert_files:
            target_function = _convert_to_m4a if convert_file.file_format == "m4a" else _convert_to_wav
            futures.append(
                executor.submit(
                    target_function, convert_file.input_file_path, convert_file.output_file_path,
                    convert_file.max_duration
                )
            )

        for future in futures:
            future.result()

    logger.info(f"Finished converting {len(convert_files)} files")


@contextmanager
def convert_files_manager(*convert_files: FileToConvert) -> None | str | list[str]:
    try:
        thread_list = []
        list_objects = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for convert_file in convert_files:
                file_format = ".m4a" if convert_file.file_format == "m4a" else ".wav"
                filename = tempfile.NamedTemporaryFile(suffix=file_format)
                target_function = _convert_to_m4a if convert_file.file_format == "m4a" else _convert_to_wav
                thread_list.append(
                    executor.submit(
                        target_function, convert_file.input_file_path, filename.name, convert_file.max_duration
                    )
                )
                list_objects.append(filename)
            for thread in thread_list:
                thread.result()
        converted_files = [obj.name for obj in list_objects]
        if len(converted_files) == 0:
            yield None
        elif len(converted_files) == 1:
            yield converted_files[0]
        else:
            yield converted_files
    finally:
        for obj in list_objects:
            obj.close()


def _convert_to_wav(input_file_path, output_file_path, max_duration):
    _run_subprocess(f"ffmpeg -y -hide_banner -loglevel error -t {max_duration} -i {input_file_path} -ar 44100 {output_file_path}")


def _convert_to_m4a(input_file_path, output_file_path, max_duration):
    _run_subprocess(f"ffmpeg -y -hide_banner -loglevel error -t {max_duration} -i {input_file_path} -c:a aac -b:a 192k -ar 44100 -movflags +faststart {output_file_path}")


def _run_subprocess(command):
    try:
        process = subprocess.run(command, shell=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        invalid_file_errors = [
            "Invalid data found when processing input",
            "Output file #0 does not contain any stream",
            "Output file does not contain any stream",
            "Invalid argument"
        ]
        if any(error in exc.stderr.decode() for error in invalid_file_errors):
            logger.warning(
               "Could not convert because the file is invalid",
                extra={"props": {"stderr": exc.stderr.decode(), "stdout": exc.stdout.decode()}}
            )
            raise ValidationError(
                f"Could not convert because the file is invalid, ffmpeg stderr: {exc.stderr.decode()}"
            ) from exc

        raise FileConversionError(
            f"Fatal error during conversion, ffmpeg stderr: {exc.stderr.decode()}"
        ) from exc
    else:
        if process.stderr:
            logger.warning(
                "Non-falal error during conversion",
                extra={"props": {"stderr": process.stderr.decode(), "stdout": process.stdout.decode()}}
            )
        logger.info(f"Conversion output: {process.stdout.decode()}")
