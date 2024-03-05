import os
import subprocess
from pathlib import Path

import pytest

from maestro_worker_python.convert_files import (
    FileConversionError,
    FileToConvert,
    convert_files,
    convert_files_manager,
)
from maestro_worker_python.response import ValidationError

TEST_PATH = Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def invalid_audio_file(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "invalid_audio.mov"
    fn.write_bytes(b"")
    return fn


@pytest.fixture(scope="session")
def corrupt_audio_file(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "corrupt_audio.mp3"
    fn.write_bytes(b"ID3")
    return fn


@pytest.mark.parametrize("file_format", ["m4a", "wav"])
def test_should_re_raise_exceptions_in_thread(invalid_audio_file, file_format):
    with pytest.raises(FileConversionError) as exc:
        convert_files(
            [
                FileToConvert(
                    input_file_path=TEST_PATH / "foobar.mp3",
                    output_file_path=f"{invalid_audio_file}.wav",
                    file_format=file_format,
                )
            ]
        )


@pytest.mark.parametrize("file_format", ["m4a", "wav"])
def test_should_raise_validation_error_if_audio_file_is_invalid(
    invalid_audio_file, file_format
):
    with pytest.raises(ValidationError) as exc:
        convert_files(
            [
                FileToConvert(
                    input_file_path=invalid_audio_file,
                    output_file_path=f"{invalid_audio_file}.wav",
                    file_format=file_format,
                )
            ]
        )

    assert "Invalid data" in str(exc.value)


@pytest.mark.parametrize("file_format", ["m4a", "wav"])
def test_should_raise_validation_error_if_audio_file_is_corrupt(
    corrupt_audio_file, file_format
):
    with pytest.raises(ValidationError) as exc:
        convert_files(
            [
                FileToConvert(
                    input_file_path=corrupt_audio_file,
                    output_file_path=f"{corrupt_audio_file}.wav",
                    file_format=file_format,
                )
            ]
        )

    assert "Invalid argument" in str(exc.value)


@pytest.mark.parametrize("file_format", ["m4a", "wav"])
def test_should_raise_validation_error_if_source_has_no_audio(file_format, caplog):
    input_file_path, output_file_path = (
        TEST_PATH / "video-no-audio.mp4",
        TEST_PATH / "output.wav",
    )
    with pytest.raises(ValidationError) as exc:
        convert_files(
            [
                FileToConvert(
                    input_file_path=input_file_path,
                    output_file_path=output_file_path,
                    file_format=file_format,
                )
            ]
        )

    assert "does not contain any strea" in str(exc.value)


@pytest.mark.parametrize(
    "input_name, output_name, format, sample_rate",
    [
        ("silent.ogg", "converted_44100.wav", "wav", 44100),
        ("silent with space.ogg", "converted_44100.wav", "wav", 44100),
        ("silent.ogg", "converted_48000.wav", "wav", 48000),
        ("silent with space.ogg", "converted_48000.wav", "wav", 48000),
    ],
)
def test_should_convert_valid_wav_audio_file(input_name, output_name, format, sample_rate):
    input_file_path, output_file_path = (
        TEST_PATH / input_name,
        TEST_PATH / output_name,
    )
    convert_files(
        [
            FileToConvert(
                input_file_path=input_file_path,
                output_file_path=output_file_path,
                file_format=format,
                sample_rate=sample_rate,
            )
        ]
    )
    assert _get_hash(input_file_path, sample_rate) == _get_hash(output_file_path, sample_rate)
    Path(output_file_path).unlink(missing_ok=True)


@pytest.mark.parametrize(
    "input_name, output_name, format, sample_rate",
    [
        ("silent.ogg", "converted_44100.m4a", "m4a", 44100),
        ("silent with space.wav", "converted_44100.m4a", "m4a", 44100),
        ("silent.ogg", "converted_48000.m4a", "m4a", 48000),
        ("silent with space.wav", "converted_48000.m4a", "m4a", 48000),
    ],
)
def test_should_convert_valid_m4a_audio_file(input_name, output_name, format, sample_rate):
    input_file_path, output_file_path = (
        TEST_PATH / input_name,
        TEST_PATH / output_name,
    )
    convert_files(
        [
            FileToConvert(
                input_file_path=input_file_path,
                output_file_path=output_file_path,
                file_format=format,
                sample_rate=sample_rate,
            )
        ]
    )
    Path(output_file_path).unlink(missing_ok=True)


def test_should_convert_multiple_valid_audio_files_and_delete_after_context():
    input_file_path, output_file_path = (
        TEST_PATH / "silent.ogg",
        TEST_PATH / "silent.wav",
    )
    converted_files_list = []
    with convert_files_manager(
        FileToConvert(
            input_file_path=input_file_path,
            output_file_path=output_file_path,
            file_format="wav",
        ),
        FileToConvert(
            input_file_path=input_file_path,
            output_file_path=output_file_path,
            file_format="wav",
        ),
    ) as converted_files:
        converted_files_list = converted_files
    result = [os.path.exists(path) for path in converted_files_list]
    assert all(result) == False


def _get_hash(file_name, sample_rate):
    command = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-i",
        str(file_name),
        "-ar",
        str(sample_rate),
        "-map",
        "0",
        "-f",
        "hash",
        "-"
    ]

    process = subprocess.run(command, shell=False, capture_output=True, check=True)
    return process.stdout.split(b"=")[1].strip()
