import time


class CircuitBreaker:
    """Salta i provider morti dopo N fallimenti consecutivi, si riapre da solo dopo il cooldown."""

    def __init__(self, failure_threshold=3, cooldown_seconds=60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures = {}
        self._opened_at = {}

    def record_success(self, name):
        self._failures[name] = 0
        self._opened_at.pop(name, None)

    def record_failure(self, name):
        self._failures[name] = self._failures.get(name, 0) + 1
        if self._failures[name] >= self.failure_threshold:
            self._opened_at[name] = time.time()

    def is_open(self, name):
        opened = self._opened_at.get(name)
        if opened is None:
            return False
        if time.time() - opened >= self.cooldown_seconds:
            self._opened_at.pop(name, None)
            self._failures[name] = 0
            return False
        return True

    def status(self):
        nomi = set(self._failures) | set(self._opened_at)
        return {n: {"fallimenti": self._failures.get(n, 0), "aperto": self.is_open(n)} for n in nomi}
