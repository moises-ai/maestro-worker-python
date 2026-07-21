from __future__ import annotations

import concurrent.futures
import logging
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from os import PathLike

from .response import ValidationError

logger = logging.getLogger(__name__)


class FileConversionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


StrPath = str | PathLike[str]


@dataclass
class FileToConvert:
    input_file_path: StrPath
    file_format: str
    output_file_path: StrPath | None = None
    max_duration: int = 1200
    sample_rate: int | None = 44100


def convert_files(convert_files: list[FileToConvert]) -> None:
    logger.info(f"Converting {len(convert_files)} files")

    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for convert_file in convert_files:
            if convert_file.output_file_path is None:
                raise ValueError("output_file_path is required when using convert_files")
            target_function = _convert_to_m4a if convert_file.file_format == "m4a" else _convert_to_wav
            futures.append(
                executor.submit(
                    target_function,
                    convert_file.input_file_path,
                    convert_file.output_file_path,
                    convert_file.max_duration,
                    convert_file.sample_rate,
                )
            )

        for future in futures:
            future.result()

    logger.info(f"Finished converting {len(convert_files)} files")


@contextmanager
def convert_files_manager(*convert_files: FileToConvert) -> Iterator[None | str | list[str]]:
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
                        target_function,
                        convert_file.input_file_path,
                        filename.name,
                        convert_file.max_duration,
                        convert_file.sample_rate,
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


def _convert_to_wav(
    input_file_path: StrPath,
    output_file_path: StrPath,
    max_duration: int,
    sample_rate: int | None = 44100,
) -> None:
    command_list = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-t",
        str(max_duration),
        "-i",
        str(input_file_path),
    ]

    if sample_rate is not None:
        command_list.extend(["-ar", str(sample_rate)])

    command_list.append(str(output_file_path))

    _run_subprocess(command_list)


def _convert_to_m4a(
    input_file_path: StrPath,
    output_file_path: StrPath,
    max_duration: int,
    sample_rate: int | None = 44100,
) -> None:
    command_list = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-t",
        str(max_duration),
        "-i",
        str(input_file_path),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
    ]

    if sample_rate is not None:
        command_list.extend(["-ar", str(sample_rate)])

    command_list.append(str(output_file_path))

    _run_subprocess(command_list)


def _run_subprocess(command: list[str]) -> None:
    try:
        process = subprocess.run(command, shell=False, capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        invalid_file_errors = [
            "Invalid data found when processing input",
            "Output file #0 does not contain any stream",
            "Output file does not contain any stream",
            "Invalid argument",
        ]
        if any(error in exc.stderr.decode() for error in invalid_file_errors):
            logger.warning(
                "Could not convert because the file is invalid",
                extra={
                    "props": {
                        "stderr": exc.stderr.decode(),
                        "stdout": exc.stdout.decode(),
                    }
                },
            )
            raise ValidationError(
                f"Could not convert because the file is invalid, ffmpeg stderr: {exc.stderr.decode()}"
            ) from exc

        raise FileConversionError(f"Fatal error during conversion, ffmpeg stderr: {exc.stderr.decode()}") from exc
    else:
        if process.stderr:
            logger.warning(
                "Non-fatal error during conversion",
                extra={
                    "props": {
                        "stderr": process.stderr.decode(),
                        "stdout": process.stdout.decode(),
                    }
                },
            )
        logger.info(f"Conversion output: {process.stdout.decode()}")
