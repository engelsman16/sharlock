from pathlib import Path

import pytest

from sharlock.parser.json_parser import parse_entry
from sharlock.parser.known_files import KNOWN
from sharlock.parser.zip_reader import read_zip

FIXTURE_ZIP = Path(__file__).parent / "fixtures" / "sample-diagnostics.zip"


def test_read_zip_returns_flat_dict():
    entries = read_zip(FIXTURE_ZIP)
    assert isinstance(entries, dict)
    assert len(entries) > 0
    # Keys are paths relative to the top-level date-prefix directory;
    # root files are bare names, commercial/ files retain their subdir prefix.
    for key in entries:
        assert not key.startswith("/"), f"Key should not be absolute: {key}"


def test_read_zip_contains_expected_files():
    entries = read_zip(FIXTURE_ZIP)
    assert "cluster_health.json" in entries
    assert "nodes_stats.json" in entries
    assert "pending_tasks.json" in entries


def test_read_zip_values_are_bytes():
    entries = read_zip(FIXTURE_ZIP)
    for val in entries.values():
        assert isinstance(val, bytes)


def test_read_zip_rejects_non_zip(tmp_path):
    bad = tmp_path / "not_a_zip.zip"
    bad.write_bytes(b"not a zip file at all")
    with pytest.raises(ValueError, match="not a ZIP file"):
        read_zip(bad)


def test_parse_entry_valid_json():
    result = parse_entry("cluster_health.json", b'{"status": "green"}')
    assert result == {"status": "green"}


def test_parse_entry_list_json():
    result = parse_entry("shards.json", b'[{"index": "foo"}]')
    assert result == [{"index": "foo"}]


def test_parse_entry_bad_json_returns_none():
    result = parse_entry("broken.json", b"this is not json {{{")
    assert result is None


def test_parse_entry_empty_returns_none():
    result = parse_entry("empty.json", b"")
    assert result is None


def test_known_files_covers_fixture_zip():
    entries = read_zip(FIXTURE_ZIP)
    missing = [k for k in entries if k not in KNOWN]
    assert missing == [], f"Files in fixture ZIP missing from KNOWN: {missing}"


def test_known_files_values_are_unique():
    values = list(KNOWN.values())
    assert len(values) == len(set(values)), "Duplicate semantic keys in KNOWN"


def test_read_zip_corrupt_zip_raises_value_error(tmp_path):
    # EOCD with claimed CD at offset 0 — is_zipfile() returns True but ZipFile() raises BadZipFile
    eocd = (
        b"PK\x05\x06"          # end of central directory signature
        + b"\x00\x00"           # disk number
        + b"\x00\x00"           # disk with start of central directory
        + b"\x01\x00"           # records on this disk
        + b"\x01\x00"           # total records
        + b"\x2c\x00\x00\x00"  # size of central directory (44 bytes)
        + b"\x00\x00\x00\x00"  # offset of central directory (points at itself)
        + b"\x00\x00"           # comment length
    )
    corrupt = tmp_path / "corrupt.zip"
    corrupt.write_bytes(eocd)
    with pytest.raises(ValueError, match="corrupt"):
        read_zip(corrupt)
