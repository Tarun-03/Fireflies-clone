"""Single-process provider cooldown; no request content is retained."""

import threading
import time

_lock = threading.Lock()
_failures = 0
_until = 0.0


def cooling_down() -> bool:
    with _lock:
        return time.monotonic() < _until


def record_result(success: bool) -> None:
    global _failures, _until
    with _lock:
        if success:
            _failures, _until = 0, 0.0
        else:
            _failures += 1
            if _failures >= 3:
                _until = time.monotonic() + 60
                _failures = 0
