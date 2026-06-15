import tempfile
from html.parser import HTMLParser
from pathlib import Path

from sharlock.output.writer import render
from sharlock.report.builder import build_context, build_lifecycle_context
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


# ── Lifecycle context tests ───────────────────────────────────────────────────

def _ilm_parsed() -> dict:
    return {
        "ilm_explain": {
            "indices": {
                "logs-000001": {
                    "managed": True,
                    "policy": "logs-policy",
                    "phase": "hot",
                    "step": "check-rollover-ready",
                },
                "metrics-000001": {
                    "managed": True,
                    "policy": "metrics-policy",
                    "phase": "warm",
                    "step": "shrink",
                },
                "archive-000001": {
                    "managed": True,
                    "policy": "logs-policy",
                    "phase": "cold",
                    "step": "freeze",
                },
            }
        },
        "indices": {
            "logs-000001": {
                "settings": {
                    "index": {"default_pipeline": "logs-ingest"}
                }
            },
            "unmanaged-index": {},
        },
    }


def test_lifecycle_tier_bucketing():
    lc = build_lifecycle_context(_ilm_parsed())
    assert "logs-000001" in lc["tier_buckets"]["hot"]
    assert "metrics-000001" in lc["tier_buckets"]["warm"]
    assert "archive-000001" in lc["tier_buckets"]["cold"]
    assert "unmanaged-index" in lc["tier_buckets"]["unmanaged"]


def test_lifecycle_managed_vs_unmanaged():
    lc = build_lifecycle_context(_ilm_parsed())
    rows = {r["name"]: r for r in lc["rows"]}
    assert rows["logs-000001"]["managed"] is True
    assert rows["unmanaged-index"]["managed"] is False


def test_lifecycle_pipeline_from_settings():
    lc = build_lifecycle_context(_ilm_parsed())
    rows = {r["name"]: r for r in lc["rows"]}
    assert rows["logs-000001"]["pipeline"] == "logs-ingest"
    assert rows["metrics-000001"]["pipeline"] is None


def test_lifecycle_policy_groups():
    lc = build_lifecycle_context(_ilm_parsed())
    assert "logs-policy" in lc["policy_groups"]
    assert "metrics-policy" in lc["policy_groups"]
    names_in_logs = {r["name"] for r in lc["policy_groups"]["logs-policy"]}
    assert "logs-000001" in names_in_logs
    assert "archive-000001" in names_in_logs


def test_lifecycle_empty_parsed():
    lc = build_lifecycle_context({})
    assert lc["has_data"] is False
    assert lc["rows"] == []
    for tier in lc["tiers"]:
        assert lc["tier_buckets"][tier] == []


def test_lifecycle_list_format_indices():
    parsed = {
        "indices": [
            {"index": "cat-index-1", "health": "green"},
            {"index": "cat-index-2", "health": "yellow"},
        ]
    }
    lc = build_lifecycle_context(parsed)
    names = {r["name"] for r in lc["rows"]}
    assert "cat-index-1" in names
    assert "cat-index-2" in names
    for r in lc["rows"]:
        assert r["pipeline"] is None


def test_lifecycle_pipeline_none_sentinel_excluded():
    parsed = {
        "indices": {
            "my-index": {"settings": {"index": {"default_pipeline": "_none"}}}
        }
    }
    lc = build_lifecycle_context(parsed)
    row = lc["rows"][0]
    assert row["pipeline"] is None


def test_build_context_includes_lifecycle():
    ctx = build_context(_base_parsed(), [])
    assert "lifecycle" in ctx
    lc = ctx["lifecycle"]
    assert "rows" in lc
    assert "tier_buckets" in lc
    assert "policy_groups" in lc
    assert "has_data" in lc


def test_render_lifecycle_section_in_html():
    parsed = {**_base_parsed(), **_ilm_parsed()}
    ctx = build_context(parsed, [])
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        out = Path(tmp.name)
    render(ctx, out)
    content = out.read_text()
    assert "Data Lifecycle" in content
    assert "Tier Flow" in content
    assert "logs-000001" in content
    out.unlink()
