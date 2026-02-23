#!/usr/bin/env python3
"""Tiny log viewer for ProctorAI sessions."""
import json, sys, os, webbrowser, html
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

LOGS = Path(__file__).parent / "logs"

def build_html(session_dir):
    entries = []
    with open(session_dir / "session.jsonl") as f:
        for line in f:
            e = json.loads(line)
            if e.get("type") == "session_start":
                continue
            entries.append(e)

    rows = ""
    for e in entries:
        img = e.get("screenshots", [""])[0]
        img_tag = f'<img src="/img/{img}" loading="lazy">' if img else ""
        verdict = e.get("determination", "")
        color = "#c62828" if verdict == "procrastinating" else "#2e7d32"
        reasoning = html.escape(e.get("reasoning", ""))
        speech = html.escape(e.get("heckler", "—"))
        ts = e.get("timestamp", "")
        rows += f"""<tr>
            <td class="img-cell">{img_tag}<div class="ts">{ts}</div></td>
            <td class="reasoning">{reasoning}</td>
            <td class="verdict" style="color:{color}">{verdict}</td>
            <td class="speech">{speech}</td>
        </tr>\n"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>ProctorAI — {session_dir.name}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font:14px/1.5 -apple-system,system-ui,sans-serif; background:#111; color:#eee; padding:16px; }}
  h1 {{ font-size:18px; margin-bottom:12px; color:#aaa; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; padding:8px; border-bottom:2px solid #333; color:#888; position:sticky; top:0; background:#111; }}
  td {{ padding:8px; border-bottom:1px solid #222; vertical-align:top; }}
  .img-cell img {{ max-width:320px; border-radius:4px; }}
  .ts {{ font-size:11px; color:#666; margin-top:4px; }}
  .reasoning {{ max-width:400px; font-size:13px; color:#ccc; }}
  .verdict {{ font-weight:700; font-size:15px; text-transform:uppercase; white-space:nowrap; }}
  .speech {{ max-width:300px; font-size:13px; color:#f9a825; font-style:italic; }}
</style></head><body>
<h1>ProctorAI Log — {session_dir.name}</h1>
<table><tr><th>Screenshot</th><th>Reasoning</th><th>Verdict</th><th>Speech</th></tr>
{rows}
</table></body></html>"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, session_dir=None, page_html="", **kw):
        self.session_dir = session_dir
        self.page_html = page_html
        super().__init__(*a, **kw)

    def do_GET(self):
        if self.path.startswith("/img/"):
            fname = unquote(self.path[5:])
            fpath = self.session_dir / fname
            if fpath.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(fpath.read_bytes())
                return
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.page_html.encode())

    def log_message(self, *a):
        pass  # quiet


def main():
    # Pick session: argument or latest
    if len(sys.argv) > 1:
        session_dir = LOGS / sys.argv[1]
    else:
        sessions = sorted(LOGS.iterdir())
        session_dir = sessions[-1]

    page_html = build_html(session_dir)

    def handler(*a, **kw):
        return Handler(*a, session_dir=session_dir, page_html=page_html, **kw)

    port = 8484
    srv = HTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Serving {session_dir.name} at {url}")
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
