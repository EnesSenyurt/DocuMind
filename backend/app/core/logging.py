import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, with a consistent format for app + uvicorn."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # Uvicorn installs its own handlers; align them with the root config.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
