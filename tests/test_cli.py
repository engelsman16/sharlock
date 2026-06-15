import subprocess
import sys
from pathlib import Path

FIXTURE_ZIP = Path(__file__).parent / "fixtures" / "sample-diagnostics.zip"


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "sharlock.cli", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "diag_zip" in result.stdout


def test_cli_full_pipeline(tmp_path):
    out = tmp_path / "report.html"
    result = subprocess.run(
        ["uv", "run", "sharlock", str(FIXTURE_ZIP), "-o", str(out)],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out.exists()
    content = out.read_text()
    assert "my-cluster" in content
    assert "8.12.0" in content
    assert len(content) > 1000


def test_cli_missing_file(tmp_path):
    result = subprocess.run(
        ["uv", "run", "sharlock", str(tmp_path / "nonexistent.zip")],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 1
    assert "not found" in result.stderr


def test_cli_default_output_name(tmp_path):
    import shutil
    zip_copy = tmp_path / "mydiag.zip"
    shutil.copy(FIXTURE_ZIP, zip_copy)
    expected_out = tmp_path / "mydiag_report.html"
    result = subprocess.run(
        ["uv", "run", "sharlock", str(zip_copy)],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0
    assert expected_out.exists()
