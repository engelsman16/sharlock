"""
Generate a synthetic sample-diagnostics.zip for offline testing.

Mimics the file layout produced by elastic/support-diagnostics:
  https://github.com/elastic/support-diagnostics

Run once and commit the resulting sample-diagnostics.zip:
    python tests/fixtures/generate_fixtures.py
"""
import io
import json
import zipfile
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent
OUT_ZIP = FIXTURE_DIR / "sample-diagnostics.zip"
DIAG_PREFIX = "my-cluster-diagnostics-2024-01-15-12-00-00"


def _j(obj: object) -> bytes:
    return json.dumps(obj, indent=2).encode()


ENTRIES: dict[str, bytes] = {
    "cluster_health.json": _j({
        "cluster_name": "my-cluster",
        "status": "green",
        "timed_out": False,
        "number_of_nodes": 3,
        "number_of_data_nodes": 3,
        "active_primary_shards": 10,
        "active_shards": 20,
        "relocating_shards": 0,
        "initializing_shards": 0,
        "unassigned_shards": 0,
        "delayed_unassigned_shards": 0,
        "number_of_pending_tasks": 0,
        "number_of_in_flight_fetch": 0,
        "task_max_waiting_in_queue_millis": 0,
        "active_shards_percent_as_number": 100.0,
    }),
    "nodes_stats.json": _j({
        "cluster_name": "my-cluster",
        "nodes": {
            "node-1": {
                "name": "node-1",
                "host": "10.0.0.1",
                "version": "8.12.0",
                "roles": ["master", "data", "ingest"],
                "jvm": {
                    "mem": {
                        "heap_used_percent": 45,
                        "heap_used_in_bytes": 2147483648,
                        "heap_max_in_bytes": 4294967296,
                    },
                    "uptime_in_millis": 86400000,
                },
                "fs": {
                    "total": {
                        "total_in_bytes": 107374182400,
                        "free_in_bytes": 53687091200,
                        "available_in_bytes": 53687091200,
                    }
                },
                "os": {
                    "cpu": {"percent": 12},
                    "mem": {
                        "total_in_bytes": 17179869184,
                        "used_in_bytes": 8589934592,
                        "free_in_bytes": 8589934592,
                    },
                },
                "thread_pool": {
                    "search": {"queue": 0, "rejected": 0},
                    "write": {"queue": 0, "rejected": 0},
                },
            },
            "node-2": {
                "name": "node-2",
                "host": "10.0.0.2",
                "version": "8.12.0",
                "roles": ["master", "data", "ingest"],
                "jvm": {
                    "mem": {
                        "heap_used_percent": 52,
                        "heap_used_in_bytes": 2684354560,
                        "heap_max_in_bytes": 4294967296,
                    },
                    "uptime_in_millis": 86400000,
                },
                "fs": {
                    "total": {
                        "total_in_bytes": 107374182400,
                        "free_in_bytes": 21474836480,
                        "available_in_bytes": 21474836480,
                    }
                },
                "os": {
                    "cpu": {"percent": 18},
                    "mem": {
                        "total_in_bytes": 17179869184,
                        "used_in_bytes": 10737418240,
                        "free_in_bytes": 6442450944,
                    },
                },
                "thread_pool": {
                    "search": {"queue": 2, "rejected": 0},
                    "write": {"queue": 0, "rejected": 5},
                },
            },
            "node-3": {
                "name": "node-3",
                "host": "10.0.0.3",
                "version": "8.12.0",
                "roles": ["master", "data", "ingest"],
                "jvm": {
                    "mem": {
                        "heap_used_percent": 38,
                        "heap_used_in_bytes": 1610612736,
                        "heap_max_in_bytes": 4294967296,
                    },
                    "uptime_in_millis": 86400000,
                },
                "fs": {
                    "total": {
                        "total_in_bytes": 107374182400,
                        "free_in_bytes": 64424509440,
                        "available_in_bytes": 64424509440,
                    }
                },
                "os": {
                    "cpu": {"percent": 8},
                    "mem": {
                        "total_in_bytes": 17179869184,
                        "used_in_bytes": 7516192768,
                        "free_in_bytes": 9663676416,
                    },
                },
                "thread_pool": {
                    "search": {"queue": 0, "rejected": 0},
                    "write": {"queue": 0, "rejected": 0},
                },
            },
        },
    }),
    "nodes_info.json": _j({
        "cluster_name": "my-cluster",
        "nodes": {
            "node-1": {
                "name": "node-1",
                "version": "8.12.0",
                "transport_address": "10.0.0.1:9300",
                "roles": ["master", "data", "ingest"],
                "settings": {
                    "cluster": {"name": "my-cluster"},
                    "http": {"port": "9200"},
                },
                "jvm": {
                    "version": "21.0.1",
                    "vm_name": "OpenJDK 64-Bit Server VM",
                    "mem": {"heap_init_in_bytes": 4294967296, "heap_max_in_bytes": 4294967296},
                },
            }
        },
    }),
    "indices_stats.json": _j({
        "_all": {
            "primaries": {
                "docs": {"count": 1000000, "deleted": 5000},
                "store": {"size_in_bytes": 1073741824},
            },
            "total": {
                "docs": {"count": 2000000, "deleted": 10000},
                "store": {"size_in_bytes": 2147483648},
            },
        },
        "indices": {
            "logs-2024.01.15": {
                "health": "green",
                "status": "open",
                "primaries": {
                    "docs": {"count": 500000, "deleted": 0},
                    "store": {"size_in_bytes": 536870912},
                },
            },
            "metrics-2024.01.15": {
                "health": "green",
                "status": "open",
                "primaries": {
                    "docs": {"count": 500000, "deleted": 5000},
                    "store": {"size_in_bytes": 536870912},
                },
            },
        },
    }),
    "cluster_settings.json": _j({
        "persistent": {},
        "transient": {},
        "defaults": {
            "cluster": {
                "routing": {
                    "allocation": {
                        "disk": {
                            "watermark": {
                                "low": "85%",
                                "high": "90%",
                                "flood_stage": "95%",
                            }
                        }
                    }
                }
            }
        },
    }),
    "pending_tasks.json": _j({
        "tasks": []
    }),
    "cluster_state.json": _j({
        "cluster_name": "my-cluster",
        "version": 42,
        "state_uuid": "abc123",
        "master_node": "node-1",
        "nodes": {
            "node-1": {"name": "node-1", "transport_address": "10.0.0.1:9300"},
            "node-2": {"name": "node-2", "transport_address": "10.0.0.2:9300"},
            "node-3": {"name": "node-3", "transport_address": "10.0.0.3:9300"},
        },
        "metadata": {
            "cluster_uuid": "xyz789",
            "templates": {},
            "indices": {},
        },
        "routing_table": {"indices": {}},
    }),
    "shards.json": _j([
        {"index": "logs-2024.01.15", "shard": "0", "prirep": "p", "state": "STARTED",
         "docs": 500000, "store": "512mb", "ip": "10.0.0.1", "node": "node-1"},
        {"index": "logs-2024.01.15", "shard": "0", "prirep": "r", "state": "STARTED",
         "docs": 500000, "store": "512mb", "ip": "10.0.0.2", "node": "node-2"},
    ]),
    "recovery.json": _j({"shards": []}),
    "allocation.json": _j([
        {"shards": "10", "disk.indices": "1gb", "disk.used": "50gb",
         "disk.avail": "50gb", "disk.total": "100gb", "disk.percent": "50",
         "host": "10.0.0.1", "ip": "10.0.0.1", "node": "node-1"},
    ]),
    "master.json": _j([
        {"id": "node-1", "host": "10.0.0.1", "ip": "10.0.0.1", "node": "node-1"}
    ]),
    "nodes.json": _j([
        {"id": "node-1", "pid": "1234", "host": "10.0.0.1", "ip": "10.0.0.1",
         "version": "8.12.0", "name": "node-1"},
        {"id": "node-2", "pid": "1235", "host": "10.0.0.2", "ip": "10.0.0.2",
         "version": "8.12.0", "name": "node-2"},
        {"id": "node-3", "pid": "1236", "host": "10.0.0.3", "ip": "10.0.0.3",
         "version": "8.12.0", "name": "node-3"},
    ]),
    "indices.json": _j([
        {"health": "green", "status": "open", "index": "logs-2024.01.15",
         "uuid": "abc1", "pri": "1", "rep": "1", "docs.count": "500000",
         "docs.deleted": "0", "store.size": "1gb", "pri.store.size": "512mb"},
        {"health": "green", "status": "open", "index": "metrics-2024.01.15",
         "uuid": "abc2", "pri": "1", "rep": "1", "docs.count": "500000",
         "docs.deleted": "5000", "store.size": "1gb", "pri.store.size": "512mb"},
    ]),
    "version.json": _j({
        "name": "node-1",
        "cluster_name": "my-cluster",
        "cluster_uuid": "xyz789",
        "version": {
            "number": "8.12.0",
            "build_flavor": "default",
            "build_type": "deb",
            "build_hash": "abc123",
            "build_date": "2024-01-15T00:00:00.000Z",
            "build_snapshot": False,
            "lucene_version": "9.9.1",
            "minimum_wire_compatibility_version": "7.17.0",
            "minimum_index_compatibility_version": "7.0.0",
        },
        "tagline": "You Know, for Search",
    }),
    "plugins.json": _j({
        "nodes": {
            "node-1": {
                "plugins": [],
                "modules": [],
            }
        }
    }),
    "ilm_explain.json": _j({
        "indices": {}
    }),
    "template.json": _j([]),
    "component_template.json": _j({"component_templates": []}),
    "index_template.json": _j({"index_templates": []}),
    "pipeline.json": _j({}),
    "tasks.json": _j({"nodes": {}}),
}


def generate(out: Path = OUT_ZIP) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in ENTRIES.items():
            zf.writestr(f"{DIAG_PREFIX}/{name}", data)
    out.write_bytes(buf.getvalue())
    print(f"Written {out} ({out.stat().st_size:,} bytes, {len(ENTRIES)} files)")


if __name__ == "__main__":
    generate()
