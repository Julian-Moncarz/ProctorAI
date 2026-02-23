#!/usr/bin/env python3
"""Tiny log viewer for ProctorAI sessions with live reload."""
import json, sys, webbrowser, html as html_mod
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, parse_qs, urlparse

LOGS = Path(__file__).parent / "logs"

PAGE_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>ProctorAI — {session}</title>
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
<h1>ProctorAI Log — {session}</h1>
<table><thead><tr><th>Screenshot</th><th>Reasoning</th><th>Verdict</th><th>Speech</th></tr></thead>
<tbody id="rows"></tbody>
</table>
<script>
let seen = 0;
function addRow(e) {{
  const tr = document.createElement('tr');
  const img = e.screenshots && e.screenshots[0] ? `<img src="/img/${{e.screenshots[0]}}" loading="lazy">` : '';
  const color = e.determination === 'procrastinating' ? '#c62828' : '#2e7d32';
  const esc = s => {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }};
  tr.innerHTML = `<td class="img-cell">${{img}}<div class="ts">${{esc(e.timestamp||'')}}</div></td>
    <td class="reasoning">${{esc(e.reasoning||'')}}</td>
    <td class="verdict" style="color:${{color}}">${{esc(e.determination||'')}}</td>
    <td class="speech">${{esc(e.heckler||'\\u2014')}}</td>`;
  document.getElementById('rows').appendChild(tr);
  tr.scrollIntoView({{behavior:'smooth'}});
}}
async function poll() {{
  try {{
    const r = await fetch('/api/entries?after=' + seen);
    const data = await r.json();
    data.forEach(addRow);
    seen += data.length;
  }} catch(e) {{}}
}}
poll();
setInterval(poll, 5000);
</script></body></html>"""


def read_entries(session_dir):
    entries = []
    p = session_dir / "session.jsonl"
    if not p.exists():
        return entries
    with open(p) as f:
        for line in f:
            e = json.loads(line)
            if e.get("type") == "session_start":
                continue
            entries.append(e)
    return entries


class Handler(SimpleHTTPRequestHandler):
    session_dir = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/entries":
            qs = parse_qs(parsed.query)
            after = int(qs.get("after", [0])[0])
            entries = read_entries(self.session_dir)
            data = entries[after:]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            return
        if parsed.path.startswith("/img/"):
            fname = unquote(parsed.path[5:])
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
        self.wfile.write(PAGE_HTML.format(session=self.session_dir.name).encode())

    def log_message(self, *a):
        pass


def main():
    if len(sys.argv) > 1:
        session_dir = LOGS / sys.argv[1]
    else:
        sessions = sorted(LOGS.iterdir())
        session_dir = sessions[-1]

    Handler.session_dir = session_dir

    port = 8484
    srv = HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Serving {session_dir.name} at {url}")
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
