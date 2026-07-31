import pytest

from maestro_worker_python.sanitize_url import UNPARSEABLE_URL, sanitize_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        # A signed GCS read: the signature is the credential.
        (
            "https://storage.googleapis.com/bucket/song.mp3"
            "?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Signature=deadbeef",
            "https://storage.googleapis.com/bucket/song.mp3",
        ),
        ("https://user:hunter2@host/path", "https://host/path"),
        ("https://host/path#fragment", "https://host/path"),
        ("HTTPS://Storage.GoogleAPIs.COM/Bucket/Song.mp3", "https://storage.googleapis.com/Bucket/Song.mp3"),
        ("https://host:443/path", "https://host/path"),
        ("http://host:80/path", "http://host/path"),
        ("https://host:8443/path", "https://host:8443/path"),
        ("gs://My-Bucket/path/to/obj.wav?x=1", "gs://my-bucket/path/to/obj.wav"),
        ("hf://meta-llama/Llama-3/model.safetensors", "hf://meta-llama/Llama-3/model.safetensors"),
        ("file:///tmp/local.wav", "file:///tmp/local.wav"),
        ("http://[::1]:8080/path", "http://[::1]:8080/path"),
    ],
)
def test_sanitize_url_removes_credentials_and_normalizes_the_location(url, expected):
    assert sanitize_url(url) == expected


def test_sanitize_url_passes_the_path_through_without_decoding_it():
    """Decoding would let %2F be reread as a separator, naming a different object."""
    assert sanitize_url("https://host/a%2Fb/My%20Song%20(1).mp3?sig=x") == "https://host/a%2Fb/My%20Song%20(1).mp3"


def test_sanitize_url_drops_a_url_it_cannot_parse():
    assert sanitize_url("https://host:not-a-port/path") == UNPARSEABLE_URL
