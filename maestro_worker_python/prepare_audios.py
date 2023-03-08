import logging
import tempfile

from contextlib import contextmanager
from urllib.request import urlretrieve
from typing import Dict
from .convert_files import FileToConvert, convert_files


@contextmanager
def prepare_audios(dict_urls: Dict[str, str], max_duration: float):
    dst_dict = {}
    for key in dict_urls.keys():
        dst_dict[key] = {}
        dst_dict[key]['dst_file'] = tempfile.NamedTemporaryFile()
        dst_dict[key]['dst_proc_file'] = tempfile.NamedTemporaryFile(
            suffix=".wav")
    try:
        for key in dst_dict.keys():
            logging.info(
                "Downloading file from input -> %s, url -> %s, filename -> %s",
                key, dict_urls[key], dst_dict[key]['dst_file'].name)
            urlretrieve(dict_urls[key], dst_dict[key]['dst_file'].name)
            logging.info("Downloaded file to %s",
                         dst_dict[key]['dst_file'].name)
            logging.info("Shortening file to %.2f seconds.", max_duration)
            convert_files([
                FileToConvert(
                    input_file_path=dst_dict[key]['dst_file'].name,
                    output_file_path=dst_dict[key]['dst_proc_file'].name,
                    file_format="wav",
                    max_duration=max_duration,
                )
            ])
            logging.info("Saved shortened file to %s.",
                         dst_dict[key]['dst_proc_file'].name)
        yield dst_dict
    finally:
        for key in dst_dict.keys():
            dst_dict[key]['dst_file'].close()
            dst_dict[key]['dst_proc_file'].close()
