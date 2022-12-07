import logging
import subprocess
import concurrent.futures
from dataclasses import dataclass
from typing import List
from subprocess import check_call
from .response import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class FileToConvert:
    input_file_path: str
    output_file_path: str
    file_format: str
    max_duration: int = 1200


def convert_files(convert_files: List[FileToConvert]):
    logger.info(f"Converting {len(convert_files)} files")

    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for convert_file in convert_files:
            target_function = _convert_to_m4a if convert_file.file_format == "m4a" else _convert_to_wav
            futures.append(
                executor.submit(target_function, convert_file.input_file_path, convert_file.output_file_path, convert_file.max_duration)
            )

        for future in futures:
            future.result()

    logger.info(f"Finished converting {len(convert_files)} files")


def _convert_to_wav(input_file_path, output_file_path, max_duration):
    _run_subprocess(f"ffmpeg -y -hide_banner -loglevel error -t {max_duration} -i {input_file_path} -ar 44100 {output_file_path}")


def _convert_to_m4a(input_file_path, output_file_path, max_duration):
    _run_subprocess(f"ffmpeg -y -hide_banner -loglevel error -t {max_duration} -i {input_file_path} -c:a aac -b:a 192k -ar 44100 -movflags +faststart {output_file_path}")


def _run_subprocess(command):
    try:
        process = subprocess.run(command, shell=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        if "Invalid data found when processing input" in exc.stderr.decode():
            logger.warning(
                f"Could not convert file because of invalid data",
                extra={'props': {'stderr': exc.stderr.decode(), 'stdout': exc.stdout.decode()}}
            )
            raise ValidationError(
                f"Could not convert file because of invalid data: {exc.stderr.decode()}"
            ) from exc

        if "Output file #0 does not contain any stream" in exc.stderr.decode():
            logger.warning(
                f"Could not convert file because it has no audio data",
                extra={'props': {'stderr': exc.stderr.decode(), 'stdout': exc.stdout.decode()}}
            )
            raise ValidationError(
                f"Could not convert file because it has no audio data: {exc.stderr.decode()}"
            ) from exc

        logger.error(
            f"Fatal error during conversion",
            extra={'props': {'stderr': exc.stderr.decode(), 'stdout': exc.stdout.decode()}}
        )
        raise exc
    else:
        if process.stderr:
            logger.warning(
                f"Non-falal error during conversion",
                extra={'props': {'stderr': process.stderr.decode(), 'stdout': process.stdout.decode()}}
            )
        logger.info(f"Conversion output: {process.stdout.decode()}")
