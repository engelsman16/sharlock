import tempfile
from html.parser import HTMLParser
from pathlib import Path

from sharlock.output.writer import render
from sharlock.report.builder import build_context
from sharlock.rules.engine import Finding


def _base_parsed() -> dict:
    return {
        "cluster_health": {
            "cluster_name": "test-cluster",
            "status": "green",
            "number_of_nodes": 2,
            "active_shards": 10,
            "unassigned_shards": 0,
        },
        "version": {"version": {"number": "8.12.0"}},
    }


def test_build_context_keys():
    ctx = build_context(_base_parsed(), [])
    assert ctx["cluster_name"] == "test-cluster"
    assert ctx["cluster_status"] == "green"
    assert ctx["node_count"] == 2
    assert ctx["es_version"] == "8.12.0"
    assert ctx["finding_count"] == 0
    assert ctx["findings"] == {"critical": [], "warn": [], "info": []}


def test_build_context_findings_grouped():
    findings = [
        Finding(id="a", title="A", severity="critical", detail="x"),
        Finding(id="b", title="B", severity="warn", detail="y"),
        Finding(id="c", title="C", severity="info", detail="z"),
    ]
    ctx = build_context(_base_parsed(), findings)
    assert ctx["finding_count"] == 3
    assert len(ctx["findings"]["critical"]) == 1
    assert len(ctx["findings"]["warn"]) == 1
    assert len(ctx["findings"]["info"]) == 1
    assert ctx["findings"]["critical"][0]["id"] == "a"


def test_build_context_raw_files():
    parsed = _base_parsed()
    ctx = build_context(parsed, [])
    keys = {f["key"] for f in ctx["raw_files"]}
    assert "cluster_health" in keys
    assert "version" in keys


def test_render_produces_valid_html():
    ctx = build_context(_base_parsed(), [])
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        out = Path(tmp.name)

    render(ctx, out)

    content = out.read_text()
    assert len(content) > 100
    assert "test-cluster" in content
    assert "8.12.0" in content

    class StrictParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.errors = []
        def handle_error(self, msg):
            self.errors.append(msg)

    p = StrictParser()
    p.feed(content)
    assert p.errors == []

    out.unlink()


def test_render_contains_severity_sections():
    findings = [
        Finding(id="r", title="Red!", severity="critical", detail="status=red"),
    ]
    ctx = build_context(_base_parsed(), findings)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        out = Path(tmp.name)

    render(ctx, out)
    content = out.read_text()
    assert "Red!" in content
    assert "status=red" in content
    out.unlink()
