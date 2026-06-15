from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sharlock.rules.engine import Finding


def build_context(parsed: dict, findings: list[Finding]) -> dict:
    """Shape parsed data + findings into a context dict for Jinja2 templates."""
    health = parsed.get("cluster_health", {})
    version_doc = parsed.get("version", {})
    es_version = (
        version_doc.get("version", {}).get("number", "unknown")
        if isinstance(version_doc, dict)
        else "unknown"
    )

    nodes_stats = parsed.get("nodes_stats", {})
    nodes = nodes_stats.get("nodes", {}) if isinstance(nodes_stats, dict) else {}
    node_count = health.get("number_of_nodes", len(nodes))

    by_severity: dict[str, list] = {"critical": [], "warn": [], "info": []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append({
            "id": f.id,
            "title": f.title,
            "detail": f.detail,
        })

    raw_files = []
    for key, data in sorted(parsed.items()):
        raw_files.append({
            "key": key,
            "data_json": json.dumps(data, indent=2),
        })

    return {
        "cluster_name": health.get("cluster_name", nodes_stats.get("cluster_name", "unknown")),
        "cluster_status": health.get("status", "unknown"),
        "node_count": node_count,
        "es_version": es_version,
        "active_shards": health.get("active_shards", 0),
        "unassigned_shards": health.get("unassigned_shards", 0),
        "findings": by_severity,
        "finding_count": len(findings),
        "raw_files": raw_files,
    }
