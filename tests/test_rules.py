from pathlib import Path

import yaml

from sharlock.rules.engine import Finding, evaluate

RULES_PATH = Path(__file__).parent.parent / "rules" / "default.yaml"


def _eval(data: dict) -> dict[str, Finding]:
    findings = evaluate(data, rules_path=RULES_PATH)
    return {f.id: f for f in findings}


def test_red_cluster_fires():
    data = {"cluster_health": {"status": "red", "unassigned_shards": 5}}
    found = _eval(data)
    assert "red_cluster" in found
    assert found["red_cluster"].severity == "critical"


def test_yellow_cluster_fires():
    data = {"cluster_health": {"status": "yellow", "unassigned_shards": 0}}
    found = _eval(data)
    assert "yellow_cluster" in found
    assert found["yellow_cluster"].severity == "warn"


def test_green_cluster_no_fire():
    data = {"cluster_health": {"status": "green", "unassigned_shards": 0}}
    found = _eval(data)
    assert "red_cluster" not in found
    assert "yellow_cluster" not in found


def test_unassigned_shards_fires():
    data = {"cluster_health": {"status": "green", "unassigned_shards": 3}}
    found = _eval(data)
    assert "unassigned_shards" in found
    assert "3" in found["unassigned_shards"].detail


def test_high_heap_fires():
    data = {
        "nodes_stats": {
            "nodes": {
                "n1": {"jvm": {"mem": {"heap_used_percent": 90}},
                       "fs": {"total": {"available_in_bytes": 50_000_000_000}},
                       "thread_pool": {"write": {"rejected": 0}, "search": {"rejected": 0}}},
            }
        }
    }
    found = _eval(data)
    assert "high_heap" in found


def test_high_heap_does_not_fire_below_threshold():
    data = {
        "nodes_stats": {
            "nodes": {
                "n1": {"jvm": {"mem": {"heap_used_percent": 70}},
                       "fs": {"total": {"available_in_bytes": 50_000_000_000}},
                       "thread_pool": {"write": {"rejected": 0}, "search": {"rejected": 0}}},
            }
        }
    }
    found = _eval(data)
    assert "high_heap" not in found


def test_disk_low_fires():
    data = {
        "nodes_stats": {
            "nodes": {
                "n1": {"jvm": {"mem": {"heap_used_percent": 50}},
                       "fs": {"total": {"available_in_bytes": 1_000_000_000}},  # ~1 GB
                       "thread_pool": {"write": {"rejected": 0}, "search": {"rejected": 0}}},
            }
        }
    }
    found = _eval(data)
    assert "disk_low" in found
    assert found["disk_low"].severity == "critical"


def test_pending_tasks_fires_on_non_empty_list():
    data = {"pending_tasks": {"tasks": [{"priority": "HIGH", "source": "something"}]}}
    found = _eval(data)
    assert "pending_tasks" in found


def test_pending_tasks_does_not_fire_on_empty_list():
    data = {"pending_tasks": {"tasks": []}}
    found = _eval(data)
    assert "pending_tasks" not in found


def test_empty_data_produces_no_findings():
    assert evaluate({}, rules_path=RULES_PATH) == []


def test_default_rules_yaml_is_valid():
    with open(RULES_PATH) as fh:
        doc = yaml.safe_load(fh)
    assert "rules" in doc
    for rule in doc["rules"]:
        assert "id" in rule
        assert "title" in rule
        assert "severity" in rule
        assert rule["severity"] in {"info", "warn", "critical"}
        assert "condition" in rule
        assert "path" in rule["condition"]
        assert "op" in rule["condition"]


def test_ilm_step_error_fires():
    data = {
        "ilm_explain": {
            "indices": {
                "my-index": {"managed": True, "policy": "p", "phase": "hot", "step": "ERROR"}
            }
        }
    }
    found = _eval(data)
    assert "ilm_step_error" in found
    assert found["ilm_step_error"].severity == "critical"


def test_ilm_step_error_does_not_fire_on_clean_step():
    data = {
        "ilm_explain": {
            "indices": {
                "my-index": {"managed": True, "policy": "p", "phase": "hot", "step": "check-rollover-ready"}
            }
        }
    }
    found = _eval(data)
    assert "ilm_step_error" not in found


def test_ilm_policy_missing_fires():
    data = {
        "ilm_explain": {
            "indices": {
                "my-index": {"managed": True, "policy": "ghost-policy", "phase": "hot", "step": "complete"}
            }
        },
        "ilm_policies": {
            "real-policy": {"version": 1}
        },
    }
    found = _eval(data)
    assert "ilm_policy_missing" in found
    assert found["ilm_policy_missing"].severity == "warn"
    assert "ghost-policy" in found["ilm_policy_missing"].detail


def test_ilm_policy_missing_does_not_fire_when_policy_present():
    data = {
        "ilm_explain": {
            "indices": {
                "my-index": {"managed": True, "policy": "real-policy", "phase": "hot", "step": "complete"}
            }
        },
        "ilm_policies": {
            "real-policy": {"version": 1}
        },
    }
    found = _eval(data)
    assert "ilm_policy_missing" not in found


def test_ilm_policy_missing_no_fire_without_ilm_policies():
    data = {
        "ilm_explain": {
            "indices": {
                "my-index": {"managed": True, "policy": "some-policy", "phase": "hot", "step": "complete"}
            }
        }
    }
    # ilm_policies absent from data → ref_data is {} → all policies "missing"
    found = _eval(data)
    assert "ilm_policy_missing" in found


def test_ilm_paused_fires():
    data = {"ilm_status": {"operation_mode": "STOPPED"}}
    found = _eval(data)
    assert "ilm_paused" in found
    assert found["ilm_paused"].severity == "warn"


def test_ilm_paused_does_not_fire_when_running():
    data = {"ilm_status": {"operation_mode": "RUNNING"}}
    found = _eval(data)
    assert "ilm_paused" not in found


def test_high_segment_count_fires():
    data = {
        "indices_stats": {
            "indices": {"my-index": {"primaries": {"segments": {"count": 40}}}}
        }
    }
    found = _eval(data)
    assert "high_segment_count" in found
    assert found["high_segment_count"].severity == "warn"


def test_high_segment_count_does_not_fire_below_threshold():
    data = {
        "indices_stats": {
            "indices": {"my-index": {"primaries": {"segments": {"count": 10}}}}
        }
    }
    found = _eval(data)
    assert "high_segment_count" not in found


def test_bulk_rejections_fires():
    data = {
        "nodes_stats": {
            "nodes": {
                "n1": {"thread_pool": {"bulk": {"rejected": 5}}}
            }
        }
    }
    found = _eval(data)
    assert "bulk_rejections" in found
    assert found["bulk_rejections"].severity == "critical"


def test_bulk_rejections_does_not_fire_on_zero():
    data = {
        "nodes_stats": {
            "nodes": {"n1": {"thread_pool": {"bulk": {"rejected": 0}}}}
        }
    }
    found = _eval(data)
    assert "bulk_rejections" not in found


def test_ingest_failures_fires():
    data = {
        "nodes_stats": {
            "nodes": {"n1": {"ingest": {"total": {"failed": 3}}}}
        }
    }
    found = _eval(data)
    assert "ingest_failures" in found
    assert found["ingest_failures"].severity == "warn"


def test_ingest_failures_does_not_fire_on_zero():
    data = {
        "nodes_stats": {
            "nodes": {"n1": {"ingest": {"total": {"failed": 0}}}}
        }
    }
    found = _eval(data)
    assert "ingest_failures" not in found


def test_fielddata_evictions_fires():
    data = {
        "fielddata_stats": {
            "nodes": {"n1": {"indices": {"fielddata": {"evictions": 1}}}}
        }
    }
    found = _eval(data)
    assert "fielddata_evictions" in found
    assert found["fielddata_evictions"].severity == "warn"


def test_fielddata_evictions_does_not_fire_on_zero():
    data = {
        "fielddata_stats": {
            "nodes": {"n1": {"indices": {"fielddata": {"evictions": 0}}}}
        }
    }
    found = _eval(data)
    assert "fielddata_evictions" not in found


def test_dangling_indices_fires():
    data = {"dangling_indices": {"dangling_indices": [{"index_name": "orphan-1"}]}}
    found = _eval(data)
    assert "dangling_indices" in found
    assert found["dangling_indices"].severity == "info"


def test_dangling_indices_does_not_fire_on_empty():
    data = {"dangling_indices": {"dangling_indices": []}}
    found = _eval(data)
    assert "dangling_indices" not in found


def test_deprecation_warnings_fires():
    data = {"deprecation_info": {"index_settings": {"my-index": ["some-deprecation"]}}}
    found = _eval(data)
    assert "deprecation_warnings" in found
    assert found["deprecation_warnings"].severity == "info"
