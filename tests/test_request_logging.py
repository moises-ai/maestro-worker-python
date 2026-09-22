import json_logging
import pytest
from starlette.requests import Request

from maestro_worker_python.request_logging import (
    ClientSafeRequestInfoExtractor,
    register_client_safe_request_extractor,
)


def _request(client) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/health", "headers": [], "client": client})


@pytest.fixture
def extractor():
    return ClientSafeRequestInfoExtractor()


def test_reports_peer_address_when_present(extractor):
    request = _request(("10.0.0.1", 54321))
    assert extractor.get_remote_ip(request) == "10.0.0.1"
    assert extractor.get_remote_port(request) == 54321


def test_reports_empty_value_when_peer_is_gone(extractor):
    request = _request(None)
    assert extractor.get_remote_ip(request) == json_logging.EMPTY_VALUE
    assert extractor.get_remote_port(request) == json_logging.EMPTY_VALUE


def test_registration_replaces_the_fastapi_request_extractor():
    original = json_logging._framework_support_map["fastapi"]["request_info_extractor_class"]
    try:
        register_client_safe_request_extractor()
        registered = json_logging._framework_support_map["fastapi"]
        assert registered["request_info_extractor_class"] is ClientSafeRequestInfoExtractor
        # The rest of the framework wiring must survive the re-registration.
        assert registered["app_request_instrumentation_configurator"] is not None
        assert registered["response_info_extractor_class"] is not None
    finally:
        json_logging._framework_support_map["fastapi"]["request_info_extractor_class"] = original
