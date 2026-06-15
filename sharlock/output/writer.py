from pathlib import Path

import jinja2


def render(context: dict, out_path: Path) -> None:
    """Render the Jinja2 base template with context and write to out_path."""
    loader = jinja2.PackageLoader("sharlock", "report/templates")
    env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape(["html"]))
    try:
        template = env.get_template("base.html")
    except jinja2.TemplateNotFound as exc:
        raise FileNotFoundError(f"Report template not found: {exc}") from exc
    html = template.render(**context)
    try:
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Cannot write report to {out_path}: {exc}") from exc
