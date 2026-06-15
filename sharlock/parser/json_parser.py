import json
import logging

logger = logging.getLogger(__name__)


def parse_entry(name: str, raw: bytes) -> dict | list | None:
    """Decode raw bytes to a Python object; returns None on bad JSON."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Could not parse %s: %s", name, exc)
        return None
