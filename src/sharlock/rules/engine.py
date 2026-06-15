from __future__ import annotations

import importlib.resources
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_OPS = {"gt", "lt", "gte", "lte", "eq", "neq", "exists", "not_exists", "ref_not_in"}


@dataclass
class Finding:
    id: str
    title: str
    severity: str
    detail: str


def _resolve(data: dict, path: str) -> list[Any]:
    """Walk a dot-separated path through nested dicts; * expands over all keys."""
    parts = path.split(".")
    current: list[Any] = [data]
    for part in parts:
        next_: list[Any] = []
        for node in current:
            if not isinstance(node, dict):
                continue
            if part == "*":
                next_.extend(node.values())
            elif part in node:
                next_.append(node[part])
        current = next_
    return current


def _matches(values: list[Any], op: str, threshold: Any) -> list[Any]:
    """Return the subset of values that satisfy the condition."""
    matched = []
    for v in values:
        hit = False
        match op:
            case "gt":
                hit = isinstance(v, (int, float)) and v > threshold
            case "lt":
                hit = isinstance(v, (int, float)) and v < threshold
            case "gte":
                hit = isinstance(v, (int, float)) and v >= threshold
            case "lte":
                hit = isinstance(v, (int, float)) and v <= threshold
            case "eq":
                hit = v == threshold
            case "neq":
                hit = v != threshold
            case "exists":
                hit = bool(v) if isinstance(v, (list, dict, str)) else v is not None
            case "not_exists":
                hit = not (bool(v) if isinstance(v, (list, dict, str)) else v is not None)
        if hit:
            matched.append(v)
    return matched


def _default_rules_path() -> Path:
    with importlib.resources.as_file(
        importlib.resources.files("sharlock").joinpath("../../rules/default.yaml")
    ) as p:
        if p.exists():
            return p
    # fallback: look relative to this file (works in editable installs)
    candidate = Path(__file__).parent.parent.parent.parent / "rules" / "default.yaml"
    if candidate.exists():
        return candidate
    raise FileNotFoundError("Could not locate rules/default.yaml")


def evaluate(data: dict, rules_path: Path | None = None) -> list[Finding]:
    """Evaluate all rules against parsed diagnostic data; return matched findings."""
    if rules_path is None:
        rules_path = _default_rules_path()

    with open(rules_path) as fh:
        rules_doc = yaml.safe_load(fh) or {}

    findings: list[Finding] = []
    for rule in rules_doc.get("rules", []):
        rid = rule["id"]
        cond = rule["condition"]
        path = cond["path"]
        op = cond["op"]

        if op not in _OPS:
            logger.warning("Rule %s: unknown op %r — skipped", rid, op)
            continue

        values = _resolve(data, path)
        if not values:
            continue

        if op == "ref_not_in":
            ref_key = cond.get("ref", "")
            ref_data = data.get(ref_key) or {}
            matched = [v for v in values if isinstance(v, str) and v and v not in ref_data]
        else:
            threshold = cond.get("value")
            matched = _matches(values, op, threshold)
        if not matched:
            continue

        detail = ", ".join(str(v) for v in matched[:5])
        if len(matched) > 5:
            detail += f" … (+{len(matched) - 5} more)"

        findings.append(Finding(
            id=rid,
            title=rule["title"],
            severity=rule["severity"],
            detail=detail,
        ))

    return findings
