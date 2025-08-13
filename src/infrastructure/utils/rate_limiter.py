"""
# src/infrastructure/utils/rate_limiter.py

限速器, 主要是用于适配各类型的 llm, memory, ADB 客户端
"""


from dataclasses import dataclass, field
from threading import Lock
from time import monotonic, sleep


@dataclass
class RateLimiter:
    """
    API rate limiter: Ensure that the interval between two requests is >= min_interval seconds.
    """
    min_interval: float
    last_request_time: float = field(default=0.0, repr=False, compare=False)
    lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def wait_if_needed(self) -> None:
        with self.lock:
            now = monotonic()
            next_time = self.last_request_time + self.min_interval
            if next_time > now:
                sleep(next_time - now)
                self.last_request_time = next_time
            else:
                self.last_request_time = now
