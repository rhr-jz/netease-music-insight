"""The one UI asset source used by Desktop, Local Web and Online Web."""
from pathlib import Path


ASSETS = Path(__file__).resolve().parent


def document(*, inline=False):
    html = (ASSETS / "index.html").read_text(encoding="utf-8")
    if inline:
        html = html.replace('<link rel="stylesheet" href="/assets/ui.css">',
                            '<style>' + (ASSETS / "ui.css").read_text(encoding="utf-8") + '</style>')
        for name in ("bridge.js", "library.js", "app.js"):
            html = html.replace(f'<script src="/assets/{name}"></script>',
                                '<script>' + (ASSETS / name).read_text(encoding="utf-8") + '</script>')
    return html
