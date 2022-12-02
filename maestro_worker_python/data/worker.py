import logging
from time import time
import traceback
from maestro_worker_python.response import WorkerResponse, ValidationError


def your_model(input):
    return f"{input} World"


class MoisesWorker(object):
    def __init__(self):
        logging.info("Loading model...")
        self.model = your_model
        logging.info("Model loaded")

    def inference(self, input_data):
        try:
            input_example = input_data.get("input_1", "Hello")
            if len(input_example) > 25:
                raise ValidationError("input is too big")
            time_start = time()
            result = self.model(input_example)
            time_end = time()
            # Send response with the result and the time it took to process the request
            return WorkerResponse(
                billable_seconds=0,
                stats={"duration": time_end - time_start},
                result={},
            )
        finally:
            logging.info("cleaning up")
