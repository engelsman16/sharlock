from pathlib import Path

import jinja2


def render(context: dict, out_path: Path) -> None:
    """Render the Jinja2 base template with context and write to out_path."""
    loader = jinja2.PackageLoader("sharlock", "report/templates")
    env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape(["html"]))
    template = env.get_template("base.html")
    html = template.render(**context)
    out_path.write_text(html, encoding="utf-8")
