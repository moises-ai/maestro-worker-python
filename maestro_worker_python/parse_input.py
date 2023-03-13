from types import SimpleNamespace
from typing import List

def parse_input_data(input_data: dict, required_params: List[str]) -> SimpleNamespace:
    for req_key in required_params:
        if req_key not in input_data.keys():
            raise ValueError(f"Missing {req_key} in request.")

    upload_urls = SimpleNamespace(**{**input_data.get("request", {})})
    del input_data['request']

    return SimpleNamespace(**{**input_data, 'upload_urls': upload_urls},
                            max_duration=float(input_data.get("max_duration", 1200)))