# Sharlock

**Elasticsearch support-diagnostic analyzer.** Point it at a `support-diagnostics` ZIP, get a self-contained HTML report with cluster health, detected issues, ILM lifecycle view, data metrics, and a raw JSON browser.

> **Disclaimer — this is vibe-coded.**
> I kept running into the same frustration: pulling a support-diagnostics bundle and having to grep through dozens of JSON files to answer basic questions about a cluster. No tool gave me the overview I needed in one place. So I built Sharlock out of annoyance, in a single session, with AI assistance. The code works and the tests pass, but treat it accordingly — not production tooling, not an Elastic product, just a useful scratch-your-own-itch utility.

---

## What it does

Parses a ZIP produced by [elastic/support-diagnostics](https://github.com/elastic/support-diagnostics) and renders a single `.html` file you can open locally. No data leaves your machine.

**Tabs in the report:**

| Tab | Contents |
|-----|----------|
| Summary | Cluster name, status, version, node count, shard counts, issue summary |
| Issues | Detected problems grouped by severity (critical / warn / info) |
| Data Lifecycle | ILM tier swimlane (hot → warm → cold → frozen → unmanaged), per-index table, per-policy breakdown |
| Data Metrics | Index sizes, ingestion throughput, shard distribution, ingest pipeline map, active recoveries, fielddata usage, segment detail |
| Raw Data | Collapsible JSON browser for every parsed file |

---

## Install

Requires Python ≥ 3.12 and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/engelsman16/sharlock.git
cd sharlock
uv sync
```

---

## Usage

```bash
uv run sharlock path/to/diagnostics.zip
# → writes diagnostics_report.html next to the ZIP
```

Custom output path:

```bash
uv run sharlock path/to/diagnostics.zip -o /tmp/report.html
```

Custom rules file:

```bash
uv run sharlock path/to/diagnostics.zip --rules my-rules.yaml
```

---

## Detection rules

Rules live in [`rules/default.yaml`](rules/default.yaml) — plain YAML, no Python required to add new ones.

```yaml
- id: high_heap
  title: "JVM heap usage > 85% on one or more nodes"
  severity: warn          # info | warn | critical
  condition:
    path: nodes_stats.nodes.*.jvm.mem.heap_used_percent
    op: gt                # gt | lt | gte | lte | eq | neq | exists | not_exists
    value: 85
```

`*` in a path fans out over all dict keys (nodes, indices, etc.) and triggers if **any** value matches.

---

## Development

```bash
uv run pytest        # 81 tests
uv run ruff check .  # lint
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
