import time


class Timer:
    def __init__(self):
        self._starts = {}
        self._stops = {}

    def start(self, name: str):
        self._starts[name] = time.perf_counter()
        if name in self._stops:
            del self._stops[name]

    def stop(self, name: str):
        if name not in self._starts:
            raise ValueError(f"Timer {name} not started, can't be stopped.")
        self._stops[name] = time.perf_counter()

    def duration(self, name: str) -> float:
        if name not in self._starts:
            raise ValueError(f"Timer {name} not started!")

        return self._stops.get(name, time.perf_counter()) - self._starts[name]

    def duration_dict(self) -> dict[str, float]:
        return {name: self.duration(name) for name in self._starts}
