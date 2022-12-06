from maestro_worker_python.download_file import download_file


def test_download_file(httpserver):
    httpserver.expect_request("/test").respond_with_data("hello")
    url = httpserver.url_for("/test?foo=bar")

    file_name = download_file(url)
    with open(file_name) as f:
        assert f.read() == "hello"
