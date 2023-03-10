import os
from maestro_worker_python.download_file import download_file, download_files_manager


def test_download_file(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    file_name = download_file(url)
    with open(file_name) as f:
        assert f.read() == "hello"

def test_download_files_manager(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    files_content = []
    with download_files_manager([url, url]) as downloaded_files:
        for file in downloaded_files:
            with open(file) as f:
                files_content.append(f.read() == "hello")
    assert all(files_content) == True

def test_download_files_manager_delete(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    files_path_exists = []
    with download_files_manager([url, url]) as downloaded_files:
        files_path = downloaded_files
    for path in files_path:
        files_path_exists.append(os.path.exists(path))
    assert all(files_path_exists) == False