"""Access-log instrumentation hardened against a missing peer address.

json_logging 1.5.1 dereferences Starlette's ``Optional`` ``Request.client``
unguarded, so a request whose peer socket is already gone (kubelet resetting a
timed-out readiness probe, typically) loses its access-log line to a formatter
traceback on stderr. Fixed upstream in bobbui/json-logging-python#116 but
unreleased; the override below stays behaviourally identical once it ships.
"""

import json_logging
from json_logging.framework.fastapi import (
    FastAPIAppRequestInstrumentationConfigurator,
    FastAPIRequestInfoExtractor,
    FastAPIResponseInfoExtractor,
)
from json_logging.frameworks import register_framework_support


class ClientSafeRequestInfoExtractor(FastAPIRequestInfoExtractor):
    def get_remote_ip(self, request):
        return request.client.host if request.client else json_logging.EMPTY_VALUE

    def get_remote_port(self, request):
        return request.client.port if request.client else json_logging.EMPTY_VALUE


def register_client_safe_request_extractor() -> None:
    """Must run before ``init_fastapi``, which freezes the extractor in a singleton."""
    register_framework_support(
        "fastapi",
        app_configurator=None,
        app_request_instrumentation_configurator=FastAPIAppRequestInstrumentationConfigurator,
        request_info_extractor_class=ClientSafeRequestInfoExtractor,
        response_info_extractor_class=FastAPIResponseInfoExtractor,
    )
