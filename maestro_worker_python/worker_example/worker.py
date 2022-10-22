import logging
from time import time
import traceback


def your_model(input):
    return f"{input} World"


class MoisesWorker(object):
    def __init__(self):
        print("Loading model...")
        self.model = your_model
        print("Model loaded")

    def inference(self, input_data):
        try:
            input_example = input_data.get("input_1", "Hello")
            time_start = time()
            result = self.model(input_example)
            time_end = time()
            # Send response with the result and the time it took to process the request
            return {"result": result, "stats": {"duration_seconds": time_end - time_start}}
        except Exception as e:
            tb = traceback.format_exc()
            logging.exception(e)
            return {"error": str(tb)}
        finally:
            logging.info("cleaning up")
