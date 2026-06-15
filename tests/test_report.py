import tempfile
from html.parser import HTMLParser
from pathlib import Path

from sharlock.output.writer import render
from sharlock.report.builder import (
    build_context,
    build_lifecycle_context,
    build_metrics_context,
    _human_bytes,
    _human_num,
)
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


def test_lifecycle_doc_count_from_indices_stats():
    parsed = {
        **_ilm_parsed(),
        "indices_stats": {
            "indices": {
                "logs-000001": {
                    "primaries": {
                        "docs": {"count": 42000},
                        "store": {"size_in_bytes": 1073741824},
                    }
                }
            }
        },
    }
    lc = build_lifecycle_context(parsed)
    row = next(r for r in lc["rows"] if r["name"] == "logs-000001")
    assert row["doc_count"] == 42000
    assert "42,000" in row["doc_count_human"]
    assert "1.0 GB" in row["store_size"]


def test_lifecycle_policy_phase_distribution():
    lc = build_lifecycle_context(_ilm_parsed())
    dist = lc["policy_phase_dist"].get("logs-policy", {})
    assert dist.get("hot", 0) >= 1
    assert dist.get("cold", 0) >= 1


def test_lifecycle_policy_defs_extracted():
    parsed = {
        **_ilm_parsed(),
        "ilm_policies": {
            "logs-policy": {
                "version": 1,
                "policy": {"phases": {"hot": {"actions": {"rollover": {"max_age": "30d"}}}}},
            }
        },
    }
    lc = build_lifecycle_context(parsed)
    assert "logs-policy" in lc["policy_defs"]
    assert "phases" in lc["policy_defs"]["logs-policy"]


def test_lifecycle_prefers_index_settings_for_pipeline():
    parsed = {
        "indices": {
            "my-index": {"settings": {"index": {"default_pipeline": "from-indices"}}},
        },
        "index_settings": {
            "my-index": {"settings": {"index": {"default_pipeline": "from-settings"}}},
        },
    }
    lc = build_lifecycle_context(parsed)
    row = next(r for r in lc["rows"] if r["name"] == "my-index")
    assert row["pipeline"] == "from-settings"


def test_lifecycle_doc_by_index_populated():
    parsed = {
        **_ilm_parsed(),
        "indices_stats": {
            "indices": {"logs-000001": {"primaries": {"docs": {"count": 99}}}}
        },
    }
    lc = build_lifecycle_context(parsed)
    assert "logs-000001" in lc["doc_by_index"]
    assert "99" in lc["doc_by_index"]["logs-000001"]


# ── Lifecycle action field ────────────────────────────────────────────────────

def test_lifecycle_action_field():
    parsed = {
        "ilm_explain": {
            "indices": {
                "idx": {"managed": True, "policy": "p", "phase": "hot", "step": "s", "action": "rollover"}
            }
        }
    }
    lc = build_lifecycle_context(parsed)
    row = lc["rows"][0]
    assert row["action"] == "rollover"


# ── Helper functions ─────────────────────────────────────────────────────────

def test_human_bytes():
    assert _human_bytes(0) == "0.0 B"
    assert _human_bytes(1024) == "1.0 KB"
    assert _human_bytes(1024 ** 2) == "1.0 MB"
    assert _human_bytes(1024 ** 3) == "1.0 GB"
    assert _human_bytes(None) == "—"


def test_human_num():
    assert _human_num(0) == "0"
    assert _human_num(1000) == "1,000"
    assert _human_num(1000000) == "1,000,000"
    assert _human_num(None) == "—"


# ── Metrics context ───────────────────────────────────────────────────────────

def _metrics_parsed() -> dict:
    return {
        "indices_stats": {
            "indices": {
                "my-index": {
                    "primaries": {
                        "docs": {"count": 100000, "deleted": 0},
                        "store": {"size_in_bytes": 1024 ** 3},
                        "indexing": {
                            "index_total": 120000,
                            "index_time_in_millis": 60000,
                            "index_current": 0,
                        },
                        "merges": {"total": 5, "total_time_in_millis": 1000},
                        "refresh": {"total": 50},
                        "segments": {"count": 10, "memory_in_bytes": 1048576},
                    },
                    "total": {"store": {"size_in_bytes": 2 * 1024 ** 3}},
                }
            }
        },
        "nodes_stats": {
            "nodes": {
                "n1": {
                    "name": "node-1",
                    "thread_pool": {
                        "write": {"rejected": 0},
                        "bulk": {"rejected": 0},
                    },
                    "ingest": {"total": {"count": 5000, "failed": 0}},
                    "indices": {"store": {"size_in_bytes": 1024 ** 3}},
                },
                "n2": {
                    "name": "node-2",
                    "thread_pool": {
                        "write": {"rejected": 3},
                        "bulk": {"rejected": 0},
                    },
                    "ingest": {"total": {"count": 2000, "failed": 7}},
                    "indices": {"store": {"size_in_bytes": 2 * 1024 ** 3}},
                },
            }
        },
        "index_settings": {
            "my-index": {
                "settings": {
                    "index": {
                        "number_of_shards": "2",
                        "default_pipeline": "my-pipe",
                    }
                }
            }
        },
        "pipelines": {
            "my-pipe": {
                "description": "test pipeline",
                "processors": [
                    {"grok": {"field": "message"}},
                    {"date": {"field": "ts"}},
                ],
            },
            "orphan-pipe": {
                "description": "unused",
                "processors": [{"set": {"field": "x", "value": "1"}}],
            },
        },
        "shards": [
            {"index": "my-index", "shard": "0", "prirep": "p", "state": "STARTED",
             "docs": "50000", "store": "512mb", "ip": "10.0.0.1", "node": "node-1"},
            {"index": "my-index", "shard": "1", "prirep": "p", "state": "STARTED",
             "docs": "50000", "store": "512mb", "ip": "10.0.0.2", "node": "node-2"},
        ],
        "recovery": {
            "rebuilding-index": {
                "shards": [
                    {
                        "id": 0, "type": "PEER", "stage": "INDEX", "primary": True,
                        "source": {"name": "node-1"},
                        "target": {"name": "node-2"},
                        "index": {
                            "size": {
                                "total_in_bytes": 1024 ** 3,
                                "recovered_in_bytes": 512 * 1024 ** 2,
                            }
                        },
                    }
                ]
            }
        },
        "fielddata_stats": {
            "nodes": {
                "n1": {
                    "name": "node-1",
                    "indices": {"fielddata": {"memory_size_in_bytes": 0, "evictions": 0}},
                },
                "n2": {
                    "name": "node-2",
                    "indices": {"fielddata": {"memory_size_in_bytes": 2048, "evictions": 10}},
                },
            }
        },
        "segments": {
            "indices": {
                "my-index": {
                    "shards": {
                        "0": [
                            {
                                "routing": {"primary": True, "node": "n1"},
                                "num_docs": 50000,
                                "deleted_docs": 0,
                                "size_in_bytes": 512 * 1024 ** 2,
                                "compound": True,
                            },
                            {
                                "routing": {"primary": False, "node": "n2"},
                                "num_docs": 50000,
                                "deleted_docs": 0,
                                "size_in_bytes": 512 * 1024 ** 2,
                                "compound": True,
                            },
                        ]
                    }
                }
            }
        },
    }


def test_metrics_size_rows():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_size"] is True
    assert len(m["size_rows"]) == 1
    row = m["size_rows"][0]
    assert row["name"] == "my-index"
    assert row["n_shards"] == 2
    assert "512.0 MB" in row["avg_shard_size"]
    assert row["doc_count"] == 100000


def test_metrics_shard_oversized_flag():
    parsed = {
        "indices_stats": {
            "indices": {
                "fat-index": {
                    "primaries": {
                        "docs": {"count": 1},
                        "store": {"size_in_bytes": 60 * 1024 ** 3},
                    },
                    "total": {"store": {"size_in_bytes": 60 * 1024 ** 3}},
                }
            }
        },
        "index_settings": {
            "fat-index": {"settings": {"index": {"number_of_shards": "1"}}}
        },
    }
    m = build_metrics_context(parsed)
    assert m["size_rows"][0]["shard_warn"] is True


def test_metrics_ingestion_rows():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_ingestion"] is True
    row = m["ingestion_rows"][0]
    assert row["name"] == "my-index"
    assert row["ops_per_ms"] == "2.00"
    assert row["seg_count"] == 10
    assert row["high_segs"] is False
    assert row["merge_pressure"] is False


def test_metrics_merge_pressure_flag():
    parsed = {
        "indices_stats": {
            "indices": {
                "busy-index": {
                    "primaries": {
                        "docs": {"count": 1},
                        "store": {"size_in_bytes": 1},
                        "indexing": {"index_total": 1000, "index_time_in_millis": 1000},
                        "merges": {"total": 10, "total_time_in_millis": 600},
                        "refresh": {"total": 10},
                        "segments": {"count": 5},
                    },
                    "total": {"store": {"size_in_bytes": 1}},
                }
            }
        }
    }
    m = build_metrics_context(parsed)
    assert m["ingestion_rows"][0]["merge_pressure"] is True


def test_metrics_high_segment_count_flag():
    parsed = {
        "indices_stats": {
            "indices": {
                "fragmented": {
                    "primaries": {
                        "docs": {"count": 1},
                        "store": {"size_in_bytes": 1},
                        "indexing": {"index_total": 1, "index_time_in_millis": 1},
                        "merges": {"total": 0, "total_time_in_millis": 0},
                        "refresh": {"total": 1},
                        "segments": {"count": 40},
                    },
                    "total": {"store": {"size_in_bytes": 1}},
                }
            }
        }
    }
    m = build_metrics_context(parsed)
    assert m["ingestion_rows"][0]["high_segs"] is True


def test_metrics_shard_distribution():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_shard_dist"] is True
    nodes = {r["name"]: r for r in m["shard_dist_rows"]}
    assert "node-1" in nodes
    assert "node-2" in nodes
    assert nodes["node-1"]["primary_count"] == 1
    assert nodes["node-2"]["primary_count"] == 1


def test_metrics_balance_ratio():
    m = build_metrics_context(_metrics_parsed())
    assert m["balance_ratio"] == 2.0
    assert m["imbalanced"] is True


def test_metrics_pipeline_map():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_pipelines"] is True
    rows = {r["name"]: r for r in m["pipeline_rows"]}
    assert "my-pipe" in rows
    assert "orphan-pipe" in rows
    assert rows["my-pipe"]["orphaned"] is False
    assert "my-index" in rows["my-pipe"]["linked_indices"]
    assert rows["orphan-pipe"]["orphaned"] is True
    assert "grok → date" in rows["my-pipe"]["proc_chain"]


def test_metrics_active_recoveries():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_recoveries"] is True
    r = m["active_recoveries"][0]
    assert r["index"] == "rebuilding-index"
    assert r["type"] == "PEER"
    assert r["pct"] == 50
    assert r["source"] == "node-1"
    assert r["target"] == "node-2"


def test_metrics_done_recoveries_excluded():
    parsed = {
        "recovery": {
            "done-index": {
                "shards": [{"id": 0, "type": "STORE", "stage": "DONE",
                             "source": {}, "target": {},
                             "index": {"size": {"total_in_bytes": 100, "recovered_in_bytes": 100}}}]
            }
        }
    }
    m = build_metrics_context(parsed)
    assert m["has_recoveries"] is False


def test_metrics_node_pressure():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_pressure"] is True
    nodes = {r["name"]: r for r in m["pressure_rows"]}
    assert nodes["node-1"]["has_critical"] is False
    assert nodes["node-1"]["has_warn"] is False
    assert nodes["node-2"]["has_critical"] is True
    assert nodes["node-2"]["write_rejected"] == 3
    assert nodes["node-2"]["has_warn"] is True
    assert nodes["node-2"]["ingest_failed"] == 7


def test_metrics_fielddata():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_fielddata"] is True
    nodes = {r["name"]: r for r in m["fielddata_rows"]}
    assert nodes["node-1"]["has_evictions"] is False
    assert nodes["node-2"]["has_evictions"] is True
    assert nodes["node-2"]["evictions"] == 10


def test_metrics_segments():
    m = build_metrics_context(_metrics_parsed())
    assert m["has_segments"] is True
    row = m["seg_rows"][0]
    assert row["name"] == "my-index"
    assert row["compound_pct"] == 100
    assert "50,000" in row["total_docs"]


def test_metrics_empty_parsed():
    m = build_metrics_context({})
    assert m["has_size"] is False
    assert m["has_ingestion"] is False
    assert m["has_shard_dist"] is False
    assert m["has_pipelines"] is False
    assert m["has_recoveries"] is False
    assert m["has_pressure"] is False
    assert m["has_fielddata"] is False
    assert m["has_segments"] is False


def test_build_context_includes_metrics():
    ctx = build_context(_base_parsed(), [])
    assert "metrics" in ctx
    m = ctx["metrics"]
    assert "size_rows" in m
    assert "ingestion_rows" in m
    assert "shard_dist_rows" in m
    assert "pipeline_rows" in m
    assert "active_recoveries" in m
    assert "pressure_rows" in m
    assert "fielddata_rows" in m
    assert "seg_rows" in m


def test_render_metrics_section_in_html():
    parsed = {**_base_parsed(), **_metrics_parsed()}
    ctx = build_context(parsed, [])
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        out = Path(tmp.name)
    render(ctx, out)
    content = out.read_text()
    assert "Data Metrics" in content
    assert "Index Size Overview" in content
    assert "Ingestion Throughput" in content
    assert "Shard Distribution" in content
    assert "Ingest Pipeline Map" in content
    assert "my-index" in content
    out.unlink()


# ── Error handling ────────────────────────────────────────────────────────────

def test_render_unwritable_path(tmp_path):
    import os
    import stat
    import pytest

    ctx = build_context(_base_parsed(), [])
    locked_dir = tmp_path / "locked"
    locked_dir.mkdir()
    locked_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

    if os.access(str(locked_dir), os.W_OK):
        pytest.skip("Running as root or filesystem ignores permissions")

    out = locked_dir / "report.html"
    try:
        with pytest.raises(OSError):
            render(ctx, out)
    finally:
        locked_dir.chmod(stat.S_IRWXU)
