#!/usr/bin/env python3
"""Builds the agent card website (BONUS level) into an output folder."""
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

owner, out = sys.argv[1], Path(sys.argv[2])
path = next((p for p in Path("agents").glob("*.md") if p.stem.lower() == owner.lower()), None)
fields = {}
if path:
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.*?)\s*$", line)
        if m:
            fields.setdefault(m.group(1).lower(), m.group(2))

e = lambda k, d="—": html.escape(fields.get(k) or d)
rows = "".join(f"<div class=row><span>{html.escape(k)}</span><b>{html.escape(v)}</b></div>"
               for k, v in fields.items() if k not in ("agent", "passphrase", "codename"))
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
out.mkdir(parents=True, exist_ok=True)
(out / "index.html").write_text(f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Agent {e('agent', owner)} · Securinets ENIT</title>
<link rel=preconnect href=https://fonts.googleapis.com>
<link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&family=JetBrains+Mono:wght@400;700&display=swap" rel=stylesheet>
<style>
:root{{--g:#29ED00;--p:#C400ED;--ink:#0b0b0b}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f6f7f2;
font-family:'JetBrains Mono',monospace;color:var(--ink);padding:16px}}
.card{{width:min(440px,100%);background:#fff;border:2px solid var(--ink);box-shadow:8px 8px 0 var(--g);padding:28px}}
.tag{{font-family:Silkscreen;color:var(--p);letter-spacing:.1em;font-size:12px}}
h1{{font-family:Silkscreen;font-size:34px;margin:.2em 0 .1em;word-break:break-word}}
h1:before{{content:'>_ ';color:var(--g)}}
.code{{font-size:14px;color:#555;margin-bottom:18px}}
.row{{display:flex;justify-content:space-between;gap:12px;border-top:1px dashed #ccc;padding:10px 0}}
.row span{{color:#777}}.row b{{text-align:right}}
footer{{margin-top:18px;font-size:11px;color:#888}}
</style></head>
<body data-agent="{html.escape(owner.lower())}"><main class=card>
<div class=tag>SECURINETS ENIT · GIT QUEST</div>
<h1>{e('agent', owner)}</h1><div class=code>codename: <b>{e('codename')}</b></div>
{rows}
<footer>deployed by GitHub Actions · {stamp}<br>« Hack fast, defend faster. »</footer>
</main></body></html>""", encoding="utf-8")
print(f"built {out/'index.html'} for {owner}")
