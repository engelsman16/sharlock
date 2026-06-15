from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sharlock.rules.engine import Finding

_TIERS = ["hot", "warm", "cold", "frozen", "unmanaged"]


def _index_pipeline(idx_data: dict) -> str | None:
    """Extract ingest pipeline from an index settings dict. Returns None if absent or _none."""
    if not isinstance(idx_data, dict):
        return None
    settings = idx_data.get("settings") or {}
    idx_settings = (settings.get("index") or {}) if isinstance(settings, dict) else {}
    candidates = [
        idx_settings.get("default_pipeline") if isinstance(idx_settings, dict) else None,
        idx_settings.get("final_pipeline") if isinstance(idx_settings, dict) else None,
        settings.get("default_pipeline") if isinstance(settings, dict) else None,
        settings.get("final_pipeline") if isinstance(settings, dict) else None,
        idx_data.get("default_pipeline"),
        idx_data.get("final_pipeline"),
    ]
    return next((v for v in candidates if v and v != "_none"), None)


def build_lifecycle_context(parsed: dict) -> dict:
    """Build the Data Lifecycle section context from ILM and index data."""
    ilm_explain = parsed.get("ilm_explain") or {}
    indices_raw = parsed.get("indices")

    ilm_indices: dict = ilm_explain.get("indices") or {} if isinstance(ilm_explain, dict) else {}

    # Support both _settings dict format and _cat/indices list format
    indices_settings: dict = {}
    if isinstance(indices_raw, dict):
        indices_settings = indices_raw
    elif isinstance(indices_raw, list):
        for item in indices_raw:
            if isinstance(item, dict) and "index" in item:
                indices_settings[item["index"]] = item

    all_names = sorted(set(ilm_indices.keys()) | set(indices_settings.keys()))

    rows: list[dict] = []
    tier_buckets: dict[str, list[str]] = {t: [] for t in _TIERS}
    policy_groups: dict[str, list[dict]] = {}

    for name in all_names:
        ilm_info = ilm_indices.get(name) or {}
        managed = bool(ilm_info.get("managed", False))
        phase = ilm_info.get("phase", "") if managed else ""
        policy = ilm_info.get("policy", "") if managed else ""
        step = ilm_info.get("step", "") if managed else ""
        tier = phase if phase in ("hot", "warm", "cold", "frozen") else "unmanaged"
        pipeline = _index_pipeline(indices_settings.get(name) or {})

        row: dict = {
            "name": name,
            "tier": tier,
            "policy": policy or None,
            "phase": phase or None,
            "step": step or None,
            "pipeline": pipeline,
            "managed": managed,
        }
        rows.append(row)
        tier_buckets[tier].append(name)
        if policy:
            policy_groups.setdefault(policy, []).append(row)

    return {
        "tier_buckets": tier_buckets,
        "tiers": _TIERS,
        "rows": rows,
        "policy_groups": policy_groups,
        "has_data": bool(rows),
    }


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
        "lifecycle": build_lifecycle_context(parsed),
    }
