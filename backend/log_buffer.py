"""
In-memory log buffer for the Ollama service logs.

Attaches a logging.Handler to the root logger that keeps the last 1000 lines
in a deque. Call setup_log_buffer() once at application startup; read lines
back via get_log_lines().
"""
import logging
from collections import deque

_buffer: deque[str] = deque(maxlen=1000)


class _BufferHandler(logging.Handler):
    """Logging handler that appends formatted records to the shared deque."""

    def emit(self, record: logging.LogRecord) -> None:
        print(record.getMessage())  # Also print to console for real-time visibility
        _buffer.append(self.format(record))

OLLAMA_LOGGER_NAME = "ollama"

def setup_ollama_log_buffer() -> None:
    """Attach the buffer handler to the Ollama logger (idempotent)."""
    logger = logging.getLogger(OLLAMA_LOGGER_NAME)
    # Avoid attaching a second handler on hot-reload
    if any(isinstance(h, _BufferHandler) for h in logger.handlers):
        return
    handler = _BufferHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def get_ollama_log_lines() -> list[str]:
    """Return a snapshot of the buffered log lines (oldest first)."""
    return list(_buffer)
