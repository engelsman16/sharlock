import argparse
import sys
from pathlib import Path

from sharlock.output.writer import render
from sharlock.parser.json_parser import parse_entry
from sharlock.parser.known_files import KNOWN
from sharlock.parser.zip_reader import read_zip
from sharlock.report.builder import build_context
from sharlock.rules.engine import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sharlock",
        description="Analyze Elasticsearch support-diagnostics ZIPs and render an HTML report.",
    )
    parser.add_argument("diag_zip", type=Path, help="Path to diagnostics ZIP file")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output HTML path (default: <zip_stem>_report.html)",
    )
    parser.add_argument(
        "--rules", type=Path, default=None,
        help="Override bundled rules YAML",
    )
    args = parser.parse_args()

    if not args.diag_zip.exists():
        print(f"error: {args.diag_zip} not found", file=sys.stderr)
        sys.exit(1)

    out = args.output or args.diag_zip.with_name(args.diag_zip.stem + "_report.html")

    try:
        raw = read_zip(args.diag_zip)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    parsed: dict = {}
    for filename, data in raw.items():
        if filename in KNOWN:
            result = parse_entry(filename, data)
            if result is not None:
                parsed[KNOWN[filename]] = result

    try:
        findings = evaluate(parsed, rules_path=args.rules)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    context = build_context(parsed, findings)

    try:
        render(context, out)
    except (OSError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    crit = len(context["findings"]["critical"])
    warn = len(context["findings"]["warn"])
    info = len(context["findings"]["info"])
    print(
        f"✓ Report: {out}  ({crit} critical, {warn} warn, {info} info)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
