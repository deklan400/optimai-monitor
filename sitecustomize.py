from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "web" / "index.html"

CSS = '<link rel="stylesheet" href="/static/activity_chart.css?v=1">'
JS = '<script src="/static/activity_chart.js?v=1"></script>'

try:
    if INDEX.exists():
        html = INDEX.read_text(encoding="utf-8")
        changed = False
        if CSS not in html and "</head>" in html:
            html = html.replace("</head>", f"  {CSS}\n</head>", 1)
            changed = True
        if JS not in html and "</body>" in html:
            html = html.replace("</body>", f"  {JS}\n</body>", 1)
            changed = True
        if changed:
            INDEX.write_text(html, encoding="utf-8")
except Exception:
    pass
