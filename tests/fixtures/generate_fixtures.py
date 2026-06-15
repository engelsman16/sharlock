"""
Generate a synthetic sample-diagnostics.zip for offline testing.

Mimics the file layout produced by elastic/support-diagnostics:
  https://github.com/elastic/support-diagnostics

Run once and commit the resulting sample-diagnostics.zip:
    uv run python tests/fixtures/generate_fixtures.py
"""
import io
import json
import zipfile
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent
OUT_ZIP = FIXTURE_DIR / "sample-diagnostics.zip"
DIAG_PREFIX = "my-cluster-diagnostics-2024-01-15-12-00-00"

GB = 1024 ** 3
MB = 1024 ** 2


def _j(obj: object) -> bytes:
    return json.dumps(obj, indent=2).encode()


ENTRIES: dict[str, bytes] = {
    # ── Cluster health & state ───────────────────────────────────────────────
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
    "cluster_stats.json": _j({
        "cluster_name": "my-cluster",
        "status": "green",
        "indices": {
            "count": 3,
            "shards": {"total": 20, "primaries": 10},
            "docs": {"count": 1100000, "deleted": 5150},
            "store": {"size_in_bytes": 1178599424},
        },
        "nodes": {
            "count": {"total": 3, "master": 3, "data": 3, "ingest": 3},
            "jvm": {"mem": {"heap_used_in_bytes": 6442450944, "heap_max_in_bytes": 12884901888}},
            "fs": {"total_in_bytes": 322122547200, "free_in_bytes": 139586437120},
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
                            "watermark": {"low": "85%", "high": "90%", "flood_stage": "95%"}
                        }
                    }
                }
            }
        },
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
    "internal_health.json": _j({
        "status": "green",
        "indicators": {
            "master_is_stable": {"status": "green", "symptom": "The elected master node is stable."},
            "shards_availability": {"status": "green", "symptom": "All shards are available."},
            "disk": {"status": "green", "symptom": "The cluster has enough available disk space."},
        },
    }),

    # ── Nodes ────────────────────────────────────────────────────────────────
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
                "fs": {"total": {
                    "total_in_bytes": 107374182400,
                    "free_in_bytes": 53687091200,
                    "available_in_bytes": 53687091200,
                }},
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
                    "bulk": {"queue": 0, "rejected": 0},
                },
                "ingest": {"total": {"count": 320000, "time_in_millis": 16000, "current": 0, "failed": 0}},
                "indices": {"store": {"size_in_bytes": 390000000}},
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
                "fs": {"total": {
                    "total_in_bytes": 107374182400,
                    "free_in_bytes": 21474836480,
                    "available_in_bytes": 21474836480,
                }},
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
                    "bulk": {"queue": 0, "rejected": 0},
                },
                "ingest": {"total": {"count": 180000, "time_in_millis": 9000, "current": 0, "failed": 0}},
                "indices": {"store": {"size_in_bytes": 588599424}},
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
                "fs": {"total": {
                    "total_in_bytes": 107374182400,
                    "free_in_bytes": 64424509440,
                    "available_in_bytes": 64424509440,
                }},
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
                    "bulk": {"queue": 0, "rejected": 0},
                },
                "ingest": {"total": {"count": 0, "time_in_millis": 0, "current": 0, "failed": 0}},
                "indices": {"store": {"size_in_bytes": 200000000}},
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
    "nodes_usage.json": _j({
        "cluster_name": "my-cluster",
        "nodes": {
            "node-1": {
                "name": "node-1",
                "rest_actions": {"nodes.info": 5, "cluster.health": 12},
                "aggregations": {"terms": {"available": True, "usage": 200}},
            }
        },
    }),
    "nodes.json": _j([
        {"id": "node-1", "pid": "1234", "host": "10.0.0.1", "ip": "10.0.0.1",
         "version": "8.12.0", "name": "node-1"},
        {"id": "node-2", "pid": "1235", "host": "10.0.0.2", "ip": "10.0.0.2",
         "version": "8.12.0", "name": "node-2"},
        {"id": "node-3", "pid": "1236", "host": "10.0.0.3", "ip": "10.0.0.3",
         "version": "8.12.0", "name": "node-3"},
    ]),

    # ── Indices ──────────────────────────────────────────────────────────────
    "indices_stats.json": _j({
        "_all": {
            "primaries": {
                "docs": {"count": 1100000, "deleted": 5150},
                "store": {"size_in_bytes": 1178599424},
            },
            "total": {
                "docs": {"count": 2200000, "deleted": 10300},
                "store": {"size_in_bytes": 2357198848},
            },
        },
        "indices": {
            "logs-2024.01.15": {
                "primaries": {
                    "docs": {"count": 500000, "deleted": 150},
                    "store": {"size_in_bytes": 536870912},
                    "indexing": {
                        "index_total": 650000,
                        "index_time_in_millis": 32500,
                        "index_current": 0,
                        "delete_total": 0,
                        "delete_time_in_millis": 0,
                    },
                    "merges": {
                        "total": 12,
                        "total_time_in_millis": 6000,
                        "total_size_in_bytes": 1073741824,
                    },
                    "refresh": {"total": 200, "total_time_in_millis": 2000},
                    "segments": {"count": 8, "memory_in_bytes": 5242880},
                },
                "total": {
                    "docs": {"count": 1000000, "deleted": 300},
                    "store": {"size_in_bytes": 1073741824},
                },
            },
            "metrics-2024.01.15": {
                "primaries": {
                    "docs": {"count": 500000, "deleted": 5000},
                    "store": {"size_in_bytes": 536870912},
                    "indexing": {
                        "index_total": 505000,
                        "index_time_in_millis": 25250,
                        "index_current": 0,
                        "delete_total": 0,
                        "delete_time_in_millis": 0,
                    },
                    "merges": {
                        "total": 5,
                        "total_time_in_millis": 2500,
                        "total_size_in_bytes": 536870912,
                    },
                    "refresh": {"total": 100, "total_time_in_millis": 1000},
                    "segments": {"count": 5, "memory_in_bytes": 2621440},
                },
                "total": {
                    "docs": {"count": 1000000, "deleted": 10000},
                    "store": {"size_in_bytes": 1073741824},
                },
            },
            "app-events": {
                "primaries": {
                    "docs": {"count": 100000, "deleted": 0},
                    "store": {"size_in_bytes": 104857600},
                    "indexing": {
                        "index_total": 100000,
                        "index_time_in_millis": 5000,
                        "index_current": 0,
                        "delete_total": 0,
                        "delete_time_in_millis": 0,
                    },
                    "merges": {
                        "total": 2,
                        "total_time_in_millis": 1000,
                        "total_size_in_bytes": 104857600,
                    },
                    "refresh": {"total": 50, "total_time_in_millis": 500},
                    "segments": {"count": 3, "memory_in_bytes": 1048576},
                },
                "total": {
                    "docs": {"count": 200000, "deleted": 0},
                    "store": {"size_in_bytes": 209715200},
                },
            },
        },
    }),
    "indices.json": _j([
        {"health": "green", "status": "open", "index": "logs-2024.01.15",
         "uuid": "abc1", "pri": "2", "rep": "1", "docs.count": "500000",
         "docs.deleted": "150", "store.size": "1gb", "pri.store.size": "512mb"},
        {"health": "green", "status": "open", "index": "metrics-2024.01.15",
         "uuid": "abc2", "pri": "1", "rep": "1", "docs.count": "500000",
         "docs.deleted": "5000", "store.size": "1gb", "pri.store.size": "512mb"},
        {"health": "green", "status": "open", "index": "app-events",
         "uuid": "abc3", "pri": "3", "rep": "1", "docs.count": "100000",
         "docs.deleted": "0", "store.size": "200mb", "pri.store.size": "100mb"},
    ]),
    "settings.json": _j({
        "logs-2024.01.15": {
            "settings": {
                "index": {
                    "number_of_shards": "2",
                    "number_of_replicas": "1",
                    "default_pipeline": "logs-pipeline",
                    "creation_date": "1705276800000",
                    "uuid": "abc1",
                }
            }
        },
        "metrics-2024.01.15": {
            "settings": {
                "index": {
                    "number_of_shards": "1",
                    "number_of_replicas": "1",
                    "creation_date": "1705276800000",
                    "uuid": "abc2",
                }
            }
        },
        "app-events": {
            "settings": {
                "index": {
                    "number_of_shards": "3",
                    "number_of_replicas": "1",
                    "creation_date": "1705276800000",
                    "uuid": "abc3",
                }
            }
        },
    }),
    "mapping.json": _j({
        "logs-2024.01.15": {
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "message": {"type": "text"},
                    "level": {"type": "keyword"},
                    "host": {"type": "keyword"},
                }
            }
        },
        "metrics-2024.01.15": {
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "metric_name": {"type": "keyword"},
                    "value": {"type": "float"},
                }
            }
        },
        "app-events": {
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "event_type": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                }
            }
        },
    }),
    "alias.json": _j({
        "logs-2024.01.15": {"aliases": {"logs": {}}},
        "metrics-2024.01.15": {"aliases": {"metrics": {}}},
        "app-events": {"aliases": {}},
    }),
    "segments.json": _j({
        "_shards": {"total": 6, "successful": 6, "failed": 0},
        "indices": {
            "logs-2024.01.15": {
                "shards": {
                    "0": [
                        {
                            "routing": {"state": "STARTED", "primary": True, "node": "node-1"},
                            "num_docs": 250000, "deleted_docs": 100,
                            "size_in_bytes": 268435456, "memory_in_bytes": 2621440,
                            "committed": True, "search": True, "version": "8.12.0", "compound": False,
                        },
                        {
                            "routing": {"state": "STARTED", "primary": False, "node": "node-2"},
                            "num_docs": 250000, "deleted_docs": 100,
                            "size_in_bytes": 268435456, "memory_in_bytes": 2621440,
                            "committed": True, "search": True, "version": "8.12.0", "compound": False,
                        },
                    ],
                    "1": [
                        {
                            "routing": {"state": "STARTED", "primary": True, "node": "node-2"},
                            "num_docs": 250000, "deleted_docs": 50,
                            "size_in_bytes": 268435456, "memory_in_bytes": 2621440,
                            "committed": True, "search": True, "version": "8.12.0", "compound": True,
                        },
                    ],
                }
            },
            "metrics-2024.01.15": {
                "shards": {
                    "0": [
                        {
                            "routing": {"state": "STARTED", "primary": True, "node": "node-3"},
                            "num_docs": 500000, "deleted_docs": 5000,
                            "size_in_bytes": 536870912, "memory_in_bytes": 5242880,
                            "committed": True, "search": True, "version": "8.12.0", "compound": False,
                        },
                    ],
                }
            },
            "app-events": {
                "shards": {
                    "0": [
                        {
                            "routing": {"state": "STARTED", "primary": True, "node": "node-1"},
                            "num_docs": 33333, "deleted_docs": 0,
                            "size_in_bytes": 34952533, "memory_in_bytes": 512000,
                            "committed": True, "search": True, "version": "8.12.0", "compound": True,
                        },
                    ],
                    "1": [
                        {
                            "routing": {"state": "STARTED", "primary": True, "node": "node-2"},
                            "num_docs": 33334, "deleted_docs": 0,
                            "size_in_bytes": 34952534, "memory_in_bytes": 512000,
                            "committed": True, "search": True, "version": "8.12.0", "compound": True,
                        },
                    ],
                    "2": [
                        {
                            "routing": {"state": "STARTED", "primary": True, "node": "node-3"},
                            "num_docs": 33333, "deleted_docs": 0,
                            "size_in_bytes": 34952533, "memory_in_bytes": 512000,
                            "committed": True, "search": True, "version": "8.12.0", "compound": True,
                        },
                    ],
                }
            },
        },
    }),
    "fielddata_stats.json": _j({
        "_nodes": {"total": 3, "successful": 3, "failed": 0},
        "cluster_name": "my-cluster",
        "nodes": {
            "node-1": {
                "name": "node-1",
                "indices": {"fielddata": {"memory_size_in_bytes": 0, "evictions": 0}},
            },
            "node-2": {
                "name": "node-2",
                "indices": {"fielddata": {"memory_size_in_bytes": 1048576, "evictions": 5}},
            },
            "node-3": {
                "name": "node-3",
                "indices": {"fielddata": {"memory_size_in_bytes": 0, "evictions": 0}},
            },
        },
    }),

    # ── Shards / recovery ────────────────────────────────────────────────────
    "shards.json": _j([
        {"index": "logs-2024.01.15", "shard": "0", "prirep": "p", "state": "STARTED",
         "docs": "250000", "store": "256mb", "ip": "10.0.0.1", "node": "node-1"},
        {"index": "logs-2024.01.15", "shard": "0", "prirep": "r", "state": "STARTED",
         "docs": "250000", "store": "256mb", "ip": "10.0.0.2", "node": "node-2"},
        {"index": "logs-2024.01.15", "shard": "1", "prirep": "p", "state": "STARTED",
         "docs": "250000", "store": "256mb", "ip": "10.0.0.2", "node": "node-2"},
        {"index": "logs-2024.01.15", "shard": "1", "prirep": "r", "state": "STARTED",
         "docs": "250000", "store": "256mb", "ip": "10.0.0.3", "node": "node-3"},
        {"index": "metrics-2024.01.15", "shard": "0", "prirep": "p", "state": "STARTED",
         "docs": "500000", "store": "512mb", "ip": "10.0.0.3", "node": "node-3"},
        {"index": "metrics-2024.01.15", "shard": "0", "prirep": "r", "state": "STARTED",
         "docs": "500000", "store": "512mb", "ip": "10.0.0.1", "node": "node-1"},
        {"index": "app-events", "shard": "0", "prirep": "p", "state": "STARTED",
         "docs": "33333", "store": "33mb", "ip": "10.0.0.1", "node": "node-1"},
        {"index": "app-events", "shard": "1", "prirep": "p", "state": "STARTED",
         "docs": "33334", "store": "33mb", "ip": "10.0.0.2", "node": "node-2"},
        {"index": "app-events", "shard": "2", "prirep": "p", "state": "STARTED",
         "docs": "33333", "store": "33mb", "ip": "10.0.0.3", "node": "node-3"},
    ]),
    "recovery.json": _j({
        "logs-2024.01.15": {
            "shards": [
                {
                    "id": 0, "type": "STORE", "stage": "DONE", "primary": True,
                    "source": {},
                    "target": {"id": "node-1", "name": "node-1", "host": "10.0.0.1"},
                    "index": {
                        "size": {
                            "total_in_bytes": 536870912,
                            "reused_in_bytes": 536870912,
                            "recovered_in_bytes": 536870912,
                            "percent": "100.0%",
                        }
                    },
                }
            ]
        }
    }),
    "allocation.json": _j([
        {"shards": "7", "disk.indices": "745mb", "disk.used": "50gb",
         "disk.avail": "50gb", "disk.total": "100gb", "disk.percent": "50",
         "host": "10.0.0.1", "ip": "10.0.0.1", "node": "node-1"},
        {"shards": "7", "disk.indices": "821mb", "disk.used": "80gb",
         "disk.avail": "20gb", "disk.total": "100gb", "disk.percent": "80",
         "host": "10.0.0.2", "ip": "10.0.0.2", "node": "node-2"},
        {"shards": "6", "disk.indices": "562mb", "disk.used": "40gb",
         "disk.avail": "60gb", "disk.total": "100gb", "disk.percent": "40",
         "host": "10.0.0.3", "ip": "10.0.0.3", "node": "node-3"},
    ]),
    "allocation_explain.json": _j({
        "index": "app-events", "shard": 0, "primary": True,
        "current_state": "started",
        "current_node": {"id": "node-1", "name": "node-1"},
        "can_remain_on_current_node": "yes",
        "can_rebalance_cluster": "yes",
        "can_rebalance_to_other_node": "no",
        "rebalance_explanation": "Shard is already balanced.",
    }),
    "shard_stores.json": _j({
        "indices": {
            "logs-2024.01.15": {
                "shards": {
                    "0": {
                        "stores": [
                            {
                                "node-1": {"name": "node-1", "transport_address": "10.0.0.1:9300"},
                                "allocation_id": {"id": "alloc-1"},
                                "allocation": "primary",
                                "store_exception": None,
                            }
                        ]
                    }
                }
            }
        }
    }),

    # ── Pipelines, templates, tasks ─────────────────────────────────────────
    "pipeline.json": _j({
        "logs-pipeline": {
            "description": "Parse and enrich log events",
            "processors": [
                {"grok": {"field": "message", "patterns": ["%{COMBINEDAPACHELOG}"]}},
                {"date": {"field": "timestamp", "formats": ["ISO8601"]}},
                {"set": {"field": "event.ingested", "value": "{{_ingest.timestamp}}"}},
                {"geoip": {"field": "client.ip"}},
            ],
        }
    }),
    "template.json": _j([]),
    "component_template.json": _j({"component_templates": []}),
    "index_template.json": _j({"index_templates": []}),
    "tasks.json": _j({"nodes": {}}),
    "pending_tasks.json": _j({"tasks": []}),

    # ── ILM ──────────────────────────────────────────────────────────────────
    "ilm_explain.json": _j({
        "indices": {
            "logs-2024.01.15": {
                "index": "logs-2024.01.15",
                "managed": True,
                "policy": "logs-policy",
                "phase": "hot",
                "action": "rollover",
                "step": "check-rollover-ready",
            },
            "metrics-2024.01.15": {
                "index": "metrics-2024.01.15",
                "managed": True,
                "policy": "metrics-policy",
                "phase": "warm",
                "action": "shrink",
                "step": "shrink",
            },
        }
    }),

    # ── Other cluster APIs ───────────────────────────────────────────────────
    "master.json": _j([
        {"id": "node-1", "host": "10.0.0.1", "ip": "10.0.0.1", "node": "node-1"}
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
            "node-1": {"plugins": [], "modules": []},
        }
    }),
    "dangling_indices.json": _j({"dangling_indices": []}),
    "deprecation_info.json": _j({
        "cluster_settings": [],
        "ml_settings": [],
        "node_settings": [],
        "index_settings": {},
    }),
    "licenses.json": _j({
        "license": {
            "status": "active",
            "uid": "lic-uuid-1",
            "type": "enterprise",
            "expiry_date_in_millis": 1893456000000,
        }
    }),
    "repositories.json": _j({"repositories": []}),
    "snapshot.json": _j({"snapshots": []}),
    "remote_cluster_info.json": _j({}),

    # ── Commercial ───────────────────────────────────────────────────────────
    "commercial/data_stream.json": _j({"data_streams": []}),
    "commercial/ilm_policies.json": _j({
        "logs-policy": {
            "version": 1,
            "policy": {
                "phases": {
                    "hot": {"actions": {"rollover": {"max_age": "30d", "max_size": "50gb"}}},
                    "warm": {"min_age": "30d", "actions": {"shrink": {"number_of_shards": 1}}},
                    "delete": {"min_age": "90d", "actions": {"delete": {}}},
                }
            },
        },
        "metrics-policy": {
            "version": 1,
            "policy": {
                "phases": {
                    "hot": {"actions": {"rollover": {"max_age": "7d", "max_docs": 5000000}}},
                    "warm": {"min_age": "7d", "actions": {"shrink": {"number_of_shards": 1}}},
                    "cold": {"min_age": "30d", "actions": {"freeze": {}}},
                    "delete": {"min_age": "365d", "actions": {"delete": {}}},
                }
            },
        },
    }),
    "commercial/ilm_explain_only_errors.json": _j({"indices": {}}),
    "commercial/ilm_status.json": _j({"operation_mode": "RUNNING"}),
    "commercial/slm_policies.json": _j({}),
    "commercial/slm_stats.json": _j({
        "retention_runs": 5,
        "retention_failed": 0,
        "retention_timed_out": 0,
        "retention_deletion_time_millis": 1200,
        "total_snapshots_taken": 15,
        "total_snapshots_failed": 0,
        "total_snapshots_deleted": 5,
        "total_snapshot_deletion_failures": 0,
        "policy_stats": [],
    }),
    "commercial/enrich_policies.json": _j({"policies": []}),
    "commercial/transform.json": _j({"transforms": []}),
    "commercial/transform_stats.json": _j({"transforms": [], "count": 0}),
    "commercial/ml_anomaly_detectors.json": _j({"jobs": [], "count": 0}),
    "commercial/ml_stats.json": _j({"jobs": [], "count": 0}),
    "commercial/ml_memory_stats.json": _j({"nodes": {}}),
    "commercial/ml_trained_models.json": _j({"trained_model_configs": [], "count": 0}),
    "commercial/ml_trained_models_stats.json": _j({"trained_model_stats": [], "count": 0}),
    "commercial/inference.json": _j({"endpoints": []}),
    "commercial/ccr_stats.json": _j({
        "auto_follow_stats": {
            "number_of_failed_follow_indices": 0,
            "number_of_failed_remote_cluster_state_requests": 0,
            "number_of_successful_follow_indices": 0,
        },
        "follow_stats": {"indices": []},
    }),
    "commercial/ccr_follower_info.json": _j({"follower_indices": []}),
    "commercial/searchable_snapshots_stats.json": _j({"total": {"num_requests": 0}}),
    "commercial/watcher_stats.json": _j({
        "manually_stopped": False,
        "stats": [{"state": "started", "watch_count": 0}],
    }),
    "commercial/security_roles.json": _j({}),
    "commercial/security_users.json": _j({}),
    "commercial/xpack.json": _j({
        "build": {"hash": "abc123", "date": "2024-01-15T00:00:00.000Z"},
        "license": {"uid": "lic-uuid-1", "type": "enterprise", "status": "active"},
        "features": {
            "ilm": {"available": True, "enabled": True},
            "ml": {"available": True, "enabled": True},
            "security": {"available": True, "enabled": True},
        },
    }),
    "commercial/autoscaling_capacity.json": _j({"policies": {}}),
    "commercial/connectors.json": _j({"connectors": [], "count": 0}),
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
