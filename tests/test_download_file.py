import logging
import os

import pytest

from maestro_worker_python.download_file import download_file, download_files_manager
from maestro_worker_python.response import ValidationError

SIGNED_QUERY = "X-Goog-Signature=deadbeefcafe"


def _assert_no_signing_material_logged(caplog, httpserver):
    # The in-process test server logs the request line it received, query included.
    # That is the fixture's own access log, not the library under test.
    records = [record for record in caplog.records if record.name != "werkzeug"]
    assert records, "nothing was logged, so this proves nothing"
    for record in records:
        message = record.getMessage()
        assert "deadbeefcafe" not in message
        assert "X-Goog-Signature" not in message
    # The sanitized location must still be logged, or redaction has cost the
    # operator the ability to tell which input a download refers to.
    assert any(httpserver.url_for("/test") in record.getMessage() for record in records)


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
        assert isinstance(downloaded_files, list)
        for file in downloaded_files:
            with open(file) as f:
                files_content.append(f.read() == "hello")
    assert all(files_content)


def test_download_file_keeps_signing_material_out_of_the_logs(httpserver, caplog):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for(f"/test?{SIGNED_QUERY}")

    with caplog.at_level(logging.INFO):
        download_file(url)

    _assert_no_signing_material_logged(caplog, httpserver)


def test_download_files_manager_keeps_signing_material_out_of_the_logs(httpserver, caplog):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for(f"/test?{SIGNED_QUERY}")

    with caplog.at_level(logging.INFO), download_files_manager(url) as downloaded:
        assert downloaded is not None

    _assert_no_signing_material_logged(caplog, httpserver)


def test_download_files_manager_delete(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    files_path_exists = []
    with download_files_manager(url, url) as downloaded_files:
        assert isinstance(downloaded_files, list)
        files_path = downloaded_files
    for path in files_path:
        files_path_exists.append(os.path.exists(path))
    assert not any(files_path_exists)
