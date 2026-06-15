from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sharlock.rules.engine import Finding

_TIERS = ["hot", "warm", "cold", "frozen", "unmanaged"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _human_bytes(n: int | float | None) -> str:
    if n is None:
        return "—"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:,.1f} {unit}"
        n /= 1024.0
    return f"{n:,.1f} PB"


def _human_num(n: int | None) -> str:
    if n is None:
        return "—"
    return f"{int(n):,}"


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


# ── Lifecycle context ─────────────────────────────────────────────────────────

def build_lifecycle_context(parsed: dict) -> dict:
    """Build Data Lifecycle section context from ILM, index, and stats data."""
    ilm_explain = parsed.get("ilm_explain") or {}
    ilm_policies = parsed.get("ilm_policies") or {}
    indices_raw = parsed.get("indices")
    index_settings = parsed.get("index_settings") or {}
    indices_stats = parsed.get("indices_stats") or {}

    ilm_indices: dict = (ilm_explain.get("indices") or {}) if isinstance(ilm_explain, dict) else {}
    stats_by_index: dict = (indices_stats.get("indices") or {}) if isinstance(indices_stats, dict) else {}

    # Build index name → cat-row dict for fallback pipeline lookup
    cat_indices: dict = {}
    if isinstance(indices_raw, dict):
        cat_indices = indices_raw
    elif isinstance(indices_raw, list):
        for item in indices_raw:
            if isinstance(item, dict) and "index" in item:
                cat_indices[item["index"]] = item

    all_names = sorted(set(ilm_indices.keys()) | set(cat_indices.keys()) | set(index_settings.keys()))

    rows: list[dict] = []
    tier_buckets: dict[str, list[str]] = {t: [] for t in _TIERS}
    doc_by_index: dict[str, str] = {}
    policy_groups: dict[str, list[dict]] = {}
    policy_phase_dist: dict[str, dict[str, int]] = {}

    for name in all_names:
        ilm_info = ilm_indices.get(name) or {}
        managed = bool(ilm_info.get("managed", False))
        phase = ilm_info.get("phase", "") if managed else ""
        policy = ilm_info.get("policy", "") if managed else ""
        step = ilm_info.get("step", "") if managed else ""
        action = ilm_info.get("action", "") if managed else ""
        tier = phase if phase in ("hot", "warm", "cold", "frozen") else "unmanaged"

        # Prefer settings.json data, fall back to indices.json
        pipeline = (
            _index_pipeline(index_settings.get(name) or {})
            or _index_pipeline(cat_indices.get(name) or {})
        )

        # Doc count + store size from indices_stats
        stats = stats_by_index.get(name) or {}
        primaries = stats.get("primaries") or {}
        doc_count: int | None = (primaries.get("docs") or {}).get("count")
        store_bytes: int | None = (primaries.get("store") or {}).get("size_in_bytes")

        row: dict = {
            "name": name,
            "tier": tier,
            "policy": policy or None,
            "phase": phase or None,
            "step": step or None,
            "action": action or None,
            "pipeline": pipeline,
            "managed": managed,
            "doc_count": doc_count,
            "doc_count_human": _human_num(doc_count),
            "store_size": _human_bytes(store_bytes),
        }
        rows.append(row)
        tier_buckets[tier].append(name)
        doc_by_index[name] = _human_num(doc_count)

        if policy:
            policy_groups.setdefault(policy, []).append(row)
            dist = policy_phase_dist.setdefault(policy, {})
            dist[tier] = dist.get(tier, 0) + 1

    # Extract policy definitions from ilm_policies
    policy_defs: dict[str, dict] = {}
    if isinstance(ilm_policies, dict):
        for pname, pdef in ilm_policies.items():
            if isinstance(pdef, dict):
                policy_defs[pname] = pdef.get("policy") or pdef

    return {
        "tier_buckets": tier_buckets,
        "doc_by_index": doc_by_index,
        "tiers": _TIERS,
        "rows": rows,
        "policy_groups": policy_groups,
        "policy_phase_dist": policy_phase_dist,
        "policy_defs": policy_defs,
        "has_data": bool(rows),
    }


# ── Metrics context ───────────────────────────────────────────────────────────

def build_metrics_context(parsed: dict) -> dict:
    """Build Data Metrics section context from stats, shards, segments, and pipeline data."""
    indices_stats = parsed.get("indices_stats") or {}
    nodes_stats = parsed.get("nodes_stats") or {}
    index_settings_raw = parsed.get("index_settings") or {}
    pipelines = parsed.get("pipelines") or {}
    recovery_raw = parsed.get("recovery") or {}
    fielddata_raw = parsed.get("fielddata_stats") or {}
    segments_raw = parsed.get("segments") or {}
    shards_raw = parsed.get("shards") or []

    stats_by_index: dict = (indices_stats.get("indices") or {}) if isinstance(indices_stats, dict) else {}
    nodes: dict = (nodes_stats.get("nodes") or {}) if isinstance(nodes_stats, dict) else {}
    index_settings: dict = index_settings_raw if isinstance(index_settings_raw, dict) else {}

    # ── 2a: Index Size Overview ───────────────────────────────────────────────
    size_rows = []
    for name in sorted(stats_by_index):
        stats = stats_by_index[name] or {}
        primaries = stats.get("primaries") or {}
        total_sect = stats.get("total") or {}
        docs = (primaries.get("docs") or {}).get("count", 0) or 0
        store_bytes = (primaries.get("store") or {}).get("size_in_bytes", 0) or 0
        total_bytes = (total_sect.get("store") or {}).get("size_in_bytes", 0) or 0

        idx_sett = ((index_settings.get(name) or {}).get("settings") or {}).get("index") or {}
        n_shards = max(1, int(idx_sett.get("number_of_shards", 1) or 1))
        avg_shard_bytes = store_bytes / n_shards if n_shards else 0

        size_rows.append({
            "name": name,
            "doc_count": docs,
            "doc_count_human": _human_num(docs),
            "store_size": _human_bytes(store_bytes),
            "total_size": _human_bytes(total_bytes),
            "n_shards": n_shards,
            "avg_shard_size": _human_bytes(int(avg_shard_bytes)),
            "shard_warn": avg_shard_bytes > 50 * 1024 ** 3,
            "shard_smell": avg_shard_bytes < 1 * 1024 ** 3 and n_shards > 5,
        })

    # ── 2b: Ingestion Throughput ──────────────────────────────────────────────
    ingestion_rows = []
    for name in sorted(stats_by_index):
        stats = stats_by_index[name] or {}
        primaries = stats.get("primaries") or {}
        indexing = primaries.get("indexing") or {}
        merges = primaries.get("merges") or {}
        refresh = primaries.get("refresh") or {}
        segments = primaries.get("segments") or {}

        index_total = indexing.get("index_total", 0) or 0
        index_time_ms = indexing.get("index_time_in_millis", 0) or 0
        merge_count = merges.get("total", 0) or 0
        merge_time_ms = merges.get("total_time_in_millis", 0) or 0
        seg_count = segments.get("count", 0) or 0

        ops_per_ms: str = (
            f"{index_total / index_time_ms:.2f}" if index_time_ms > 0 else "—"
        )
        merge_pressure = (
            merge_time_ms > 0 and index_time_ms > 0
            and (merge_time_ms / index_time_ms) > 0.5
        )

        ingestion_rows.append({
            "name": name,
            "index_total": _human_num(index_total),
            "index_time_ms": _human_num(index_time_ms),
            "ops_per_ms": ops_per_ms,
            "merge_count": _human_num(merge_count),
            "merge_time_ms": _human_num(merge_time_ms),
            "refresh_count": _human_num(refresh.get("total", 0) or 0),
            "seg_count": seg_count,
            "merge_pressure": merge_pressure,
            "high_segs": seg_count > 30,
        })

    # ── 2c: Shard Distribution ────────────────────────────────────────────────
    node_data: dict[str, dict] = {}
    for node_id, node in nodes.items():
        node_name = node.get("name", node_id)
        store_bytes = ((node.get("indices") or {}).get("store") or {}).get("size_in_bytes", 0) or 0
        node_data[node_name] = {
            "name": node_name,
            "shard_count": 0,
            "primary_count": 0,
            "store_bytes": store_bytes,
            "store_size": _human_bytes(store_bytes),
        }

    if isinstance(shards_raw, list):
        for shard in shards_raw:
            if not isinstance(shard, dict):
                continue
            node_name = shard.get("node", "")
            if not node_name:
                continue
            if node_name not in node_data:
                node_data[node_name] = {
                    "name": node_name, "shard_count": 0, "primary_count": 0,
                    "store_bytes": 0, "store_size": "—",
                }
            node_data[node_name]["shard_count"] += 1
            if shard.get("prirep") == "p":
                node_data[node_name]["primary_count"] += 1

    shard_dist_rows = sorted(node_data.values(), key=lambda r: r["name"])
    store_sizes = [r["store_bytes"] for r in shard_dist_rows if r["store_bytes"] > 0]
    balance_ratio: float | None = None
    if len(store_sizes) >= 2 and min(store_sizes) > 0:
        balance_ratio = round(max(store_sizes) / min(store_sizes), 2)

    # ── 2d: Ingest Pipeline Map ───────────────────────────────────────────────
    # Build reverse map: pipeline_name → list of index names
    pipeline_index_map: dict[str, list[str]] = {}
    if isinstance(pipelines, dict):
        for pname in pipelines:
            pipeline_index_map[pname] = []

    for idx_name, idx_data in index_settings.items():
        if not isinstance(idx_data, dict):
            continue
        pipeline = _index_pipeline(idx_data)
        if not pipeline:
            continue
        pipeline_index_map.setdefault(pipeline, []).append(idx_name)

    pipeline_rows = []
    if isinstance(pipelines, dict):
        for pname, pdef in sorted(pipelines.items()):
            if not isinstance(pdef, dict):
                continue
            processors = pdef.get("processors") or []
            proc_chain = " → ".join(
                next(iter(p.keys())) for p in processors if isinstance(p, dict)
            ) or "—"
            linked = sorted(pipeline_index_map.get(pname) or [])
            pipeline_rows.append({
                "name": pname,
                "description": pdef.get("description", ""),
                "proc_chain": proc_chain,
                "proc_count": len(processors),
                "linked_indices": linked,
                "orphaned": len(linked) == 0,
            })

    # ── 2e: Active Recoveries ─────────────────────────────────────────────────
    active_recoveries = []
    if isinstance(recovery_raw, dict):
        for idx_name, idx_rec in recovery_raw.items():
            if not isinstance(idx_rec, dict):
                continue
            for shard in idx_rec.get("shards") or []:
                if not isinstance(shard, dict):
                    continue
                stage = (shard.get("stage") or "").upper()
                if stage == "DONE":
                    continue
                size_info = (shard.get("index") or {}).get("size") or {}
                total = size_info.get("total_in_bytes", 0) or 0
                recovered = size_info.get("recovered_in_bytes", 0) or 0
                pct = int(recovered / total * 100) if total > 0 else 0
                active_recoveries.append({
                    "index": idx_name,
                    "shard": shard.get("id", "?"),
                    "type": shard.get("type", "?"),
                    "stage": stage,
                    "source": (shard.get("source") or {}).get("name", "—"),
                    "target": (shard.get("target") or {}).get("name", "—"),
                    "pct": pct,
                    "recovered": _human_bytes(recovered),
                    "total": _human_bytes(total),
                })

    # ── 2f: Node Ingestion Pressure ───────────────────────────────────────────
    pressure_rows = []
    for node_id, node in nodes.items():
        node_name = node.get("name", node_id)
        tp = node.get("thread_pool") or {}
        ingest_totals = (node.get("ingest") or {}).get("total") or {}

        bulk_rejected = (tp.get("bulk") or {}).get("rejected", 0) or 0
        write_rejected = (tp.get("write") or {}).get("rejected", 0) or 0
        ingest_failed = ingest_totals.get("failed", 0) or 0
        ingest_count = ingest_totals.get("count", 0) or 0

        pressure_rows.append({
            "name": node_name,
            "bulk_rejected": bulk_rejected,
            "write_rejected": write_rejected,
            "ingest_failed": ingest_failed,
            "ingest_count": _human_num(ingest_count),
            "has_critical": bulk_rejected > 0 or write_rejected > 0,
            "has_warn": ingest_failed > 0,
        })

    # ── 2g: Fielddata Usage ───────────────────────────────────────────────────
    fielddata_rows = []
    fd_nodes: dict = (fielddata_raw.get("nodes") or {}) if isinstance(fielddata_raw, dict) else {}
    for node_id, node in fd_nodes.items():
        node_name = node.get("name", node_id)
        fd = ((node.get("indices") or {}).get("fielddata") or {})
        mem_bytes = fd.get("memory_size_in_bytes", 0) or 0
        evictions = fd.get("evictions", 0) or 0
        fielddata_rows.append({
            "name": node_name,
            "mem_size": _human_bytes(mem_bytes),
            "evictions": evictions,
            "has_evictions": evictions > 0,
        })

    # ── 2h: Segment Detail ────────────────────────────────────────────────────
    seg_rows = []
    seg_indices: dict = (segments_raw.get("indices") or {}) if isinstance(segments_raw, dict) else {}
    for idx_name in sorted(seg_indices):
        idx_data = seg_indices[idx_name] or {}
        if not isinstance(idx_data, dict):
            continue
        shards_data = idx_data.get("shards") or {}
        total_docs = 0
        total_size = 0
        total_copies = 0
        compound_copies = 0

        for shard_id, copies in shards_data.items():
            if not isinstance(copies, list):
                continue
            for copy in copies:
                if not isinstance(copy, dict):
                    continue
                routing = copy.get("routing") or {}
                if not routing.get("primary", True):
                    continue
                total_docs += copy.get("num_docs", 0) or 0
                total_size += copy.get("size_in_bytes", 0) or 0
                total_copies += 1
                if copy.get("compound", False):
                    compound_copies += 1

        compound_pct = int(compound_copies / total_copies * 100) if total_copies > 0 else 0
        seg_count = (stats_by_index.get(idx_name) or {}).get("primaries", {}).get("segments", {}).get("count", total_copies)

        seg_rows.append({
            "name": idx_name,
            "seg_count": seg_count,
            "total_docs": _human_num(total_docs),
            "total_size": _human_bytes(total_size),
            "compound_pct": compound_pct,
            "high_segs": (seg_count or 0) > 30,
        })

    return {
        "size_rows": size_rows,
        "has_size": bool(size_rows),
        "ingestion_rows": ingestion_rows,
        "has_ingestion": bool(ingestion_rows),
        "shard_dist_rows": shard_dist_rows,
        "balance_ratio": balance_ratio,
        "imbalanced": balance_ratio is not None and balance_ratio > 1.5,
        "has_shard_dist": bool(shard_dist_rows),
        "pipeline_rows": pipeline_rows,
        "has_pipelines": bool(pipeline_rows),
        "active_recoveries": active_recoveries,
        "has_recoveries": bool(active_recoveries),
        "pressure_rows": pressure_rows,
        "has_pressure": bool(pressure_rows),
        "fielddata_rows": fielddata_rows,
        "has_fielddata": bool(fielddata_rows),
        "seg_rows": seg_rows,
        "has_segments": bool(seg_rows),
    }


# ── Main context builder ──────────────────────────────────────────────────────

def build_context(parsed: dict, findings: list[Finding]) -> dict:
    """Shape parsed data + findings into a context dict for Jinja2 templates."""
    health = parsed.get("cluster_health") or {}
    version_doc = parsed.get("version") or {}
    es_version = (
        version_doc.get("version", {}).get("number", "unknown")
        if isinstance(version_doc, dict)
        else "unknown"
    )

    nodes_stats = parsed.get("nodes_stats") or {}
    nodes = nodes_stats.get("nodes") or {} if isinstance(nodes_stats, dict) else {}
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
        "metrics": build_metrics_context(parsed),
    }
