"""
==============================
|src/domains/rate_limiters.py|
==============================

# limit rate according to academic databse 
"""

from dataclasses import dataclass, field
import threading
import time


@dataclass
class RateLimiter:
    """
    API rate limiter - strictly adheres to official documentation requirements
    """

    min_interval: int
    last_request_time: float = field(default=0)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def wait_if_needed(self):
        """
        Ensure that the request interval >= 3 seconds
        """
        with self.lock:

            current_time = time.time()
            delta_time = self.min_interval - (current_time - self.last_request_time)
            if delta_time > 0:
                time.sleep(delta_time)

            self.last_request_time = time.time()