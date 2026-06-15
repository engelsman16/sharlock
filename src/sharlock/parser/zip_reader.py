import zipfile
from pathlib import Path


def read_zip(path: str | Path) -> dict[str, bytes]:
    """Open a diagnostics ZIP and return a flat filename→bytes map.

    Strips the leading date-prefixed directory (e.g. my-cluster-2024-01-15-12-00-00/).
    Raises ValueError for non-ZIP input.
    """
    path = Path(path)
    if not zipfile.is_zipfile(path):
        raise ValueError(f"{path} is not a ZIP file")

    result: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = info.filename.split("/", 1)
            name = parts[1] if len(parts) == 2 else parts[0]
            if name:
                result[name] = zf.read(info.filename)
    return result
