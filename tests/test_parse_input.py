import pytest

from types import SimpleNamespace
from maestro_worker_python.parse_input import parse_input_data

def test_fails_without_required_params_in_input_data():
    input_dict = {'audio_1': 'audio_1_content', 'audio_2': 'audio_2_content', 
                  'request': {'segments': 'segments_signed_url'}}
    required_params = ['audio_3']
    
    try:
        parse_input_data(input_dict, required_params)
    except ValueError as e:
        assert str(e) == f"Missing {required_params[0]} in request."

def test_pass_with_expected_simple_namespace():
    input_dict = {'audio_1': 'audio_1_content', 'audio_2': 'audio_2_content', 
                  'request': {'segments': 'segments_signed_url'}}
    required_params = ['audio_1', 'audio_2', 'request']

    expected_namespace = SimpleNamespace(audio_1=input_dict['audio_1'], 
                                        audio_2=input_dict['audio_2'], 
                                        upload_urls=SimpleNamespace(**input_dict['request']), 
                                        max_duration=float(input_dict.get('max_duration', 1200)))
    result = parse_input_data(input_dict, required_params)

    assert result == expected_namespace