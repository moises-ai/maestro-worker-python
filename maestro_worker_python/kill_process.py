import psutil
import logging
from contextlib import suppress


def kill_child_processes():
    current_process = psutil.Process()
    logging.info(f'Terminating everything from parent process PID: {current_process.pid}')
    
    children = current_process.children(recursive=True)
    for child in children:
        logging.info(f'Sending SIGTERM to child process PID: {child.pid}')
        with suppress(psutil.NoSuchProcess):
            child.terminate()

    _, still_alive = psutil.wait_procs(children, timeout=3)
    for p in still_alive:
        logging.warning(f'Child process PID: {p.pid} did not terminate, killing forcefully')
        with suppress(psutil.NoSuchProcess):
            p.kill()


def terminate_current_process():
    current_process = psutil.Process()
    logging.info(f'Sending SIGTERM to current process PID: {current_process.pid}')
    with suppress(psutil.NoSuchProcess):
        current_process.terminate()
