import pytest
import hashlib
import subprocess
from pathlib import Path
from maestro_worker_python.convert_files import convert_files, FileToConvert


TEST_PATH = Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def invalid_audio_file(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "invalid_audio.mp3"
    fn.write_bytes(b"invalid")
    return fn


@pytest.mark.parametrize("file_format", ["m4a", "wav"])
def test_should_re_raise_exceptions_in_thread(invalid_audio_file, file_format, caplog):
    with pytest.raises(subprocess.CalledProcessError) as exc:
        convert_files(
            [FileToConvert(
                input_file_path=invalid_audio_file,
                output_file_path=f"{invalid_audio_file}.wav",
                file_format=file_format,
            )]
        )

    assert caplog.records[0].levelname == "ERROR"
    assert caplog.records[0].message == "Fatal error during conversion"


def test_should_convert_valid_audio_file():
    input_file_path, output_file_path = TEST_PATH / "silent.ogg", TEST_PATH / "silent.wav"
    convert_files(
        [FileToConvert(
            input_file_path=input_file_path,
            output_file_path=output_file_path,
            file_format="wav",
        )]
    )
    assert _get_hash(input_file_path) == _get_hash(output_file_path)
    Path(output_file_path).unlink(missing_ok=True)


def _get_hash(file_name):
    process = subprocess.run(
        f"ffmpeg -loglevel error -i {file_name} -map 0 -f hash -",
        shell=True, capture_output=True, check=True,
    )
    return process.stdout.split(b"=")[1].strip()
