
import logging
from subprocess import check_output

def get_duration(local_file_path: str) -> int:
    logging.info(f"Getting file duration for {local_file_path}")
    duration = None
    try:
        duration = check_output(["ffprobe", "-v", "error", "-show_entries",
                               "format=duration", "-of",
                               "default=noprint_wrappers=1:nokey=1",
                               local_file_path])
        if duration == b'N/A\n':
            logging.info(f"File {local_file_path} has no valid duration")
            return None
        return int(float(duration))
    except Exception as e:
        logging.error(f"Error getting duration for {local_file_path}: {e}")
