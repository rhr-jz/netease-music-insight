"""Bounded job admission; jobs remain owned by their session's bridge."""
from threading import BoundedSemaphore


class JobManager:
    def __init__(self, maximum):
        self._slots = BoundedSemaphore(maximum)

    def acquire(self):
        return self._slots.acquire(blocking=False)

    def release(self):
        self._slots.release()
