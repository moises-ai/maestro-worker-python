import subprocess
from pathlib import Path
from maestro_worker_python.prepare_audios import prepare_audios


TEST_PATH = Path(__file__).resolve().parent


def test_should_convert_valid_audio_file(httpserver):
    input_file_path = TEST_PATH / "silent.ogg"
    with open(input_file_path, 'rb') as f:
        httpserver.expect_request("/test").respond_with_data(f.read())
    url = httpserver.url_for("/test")

    with prepare_audios(dict_urls={
        "file_1": url,
    }, max_duration=5) as prepared_audios:
        assert _get_hash(input_file_path) == _get_hash(prepared_audios["file_1"]["dst_proc_file"].name)
    assert not Path(prepared_audios["file_1"]["dst_file"].name).exists()
    assert not Path(prepared_audios["file_1"]["dst_proc_file"].name).exists()


def _get_hash(file_name):
    process = subprocess.run(
        f"ffmpeg -loglevel error -i {file_name} -map 0 -f hash -",
        shell=True, capture_output=True, check=True,
    )
    return process.stdout.split(b"=")[1].strip()
