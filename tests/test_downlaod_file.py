import os
import pytest
from maestro_worker_python.download_file import download_file, download_files_manager
from maestro_worker_python.response import ValidationError


def test_download_file(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    file_name = download_file(url)
    with open(file_name) as f:
        assert f.read() == "hello"


def test_bad_response_should_raise_validation_error(httpserver):
    httpserver.expect_request("/bad_url").respond_with_data("", status=404)
    bad_url = httpserver.url_for("/bad_url")

    with pytest.raises(ValidationError) as excinfo:
        download_file(bad_url)

    assert "Bad download input" in str(excinfo.value)


def test_download_files_manager(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    files_content = []
    with download_files_manager(url, url) as downloaded_files:
        for file in downloaded_files:
            with open(file) as f:
                files_content.append(f.read() == "hello")
    assert all(files_content) == True


def test_download_files_manager_delete(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    files_path_exists = []
    with download_files_manager(url, url) as downloaded_files:
        files_path = downloaded_files
    for path in files_path:
        files_path_exists.append(os.path.exists(path))
    assert all(files_path_exists) == False
