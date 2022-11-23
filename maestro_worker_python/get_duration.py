
import logging
from subprocess import check_output
logging.basicConfig(level=logging.INFO)


def get_duration(local_file_path: str) -> int:
    logging.info(f"Getting file duration for {local_file_path}")
    try:
        output = check_output(["ffprobe", "-v", "error", "-show_entries",
                               "format=duration", "-of",
                               "default=noprint_wrappers=1:nokey=1",
                               local_file_path])
        return int(float(output))
    except Exception as e:
        logging.error(f"Error getting duration for {local_file_path}: {e}")
