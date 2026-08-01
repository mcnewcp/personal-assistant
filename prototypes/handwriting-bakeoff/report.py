#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow"]
# ///
"""Build a local side-by-side grading page from a bake-off run.

    ./report.py          # writes results/compare.html

Photo pinned on the left, every model's transcription on the right, so you
can read one against the other without scrolling away. Self-contained (the
photo is embedded) and written to a gitignored directory — it stays on this
machine. Nothing here is uploaded anywhere.
"""

from __future__ import annotations

import base64
import html
import json
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).parent
PAGES_DIR = HERE / "pages"
RESULTS_DIR = HERE / "results"
OUT = RESULTS_DIR / "compare.html"

# Order worst-to-best is unknowable up front, so present alphabetically by
# provider grouping to avoid nudging the grader.
PROVIDER_LABEL = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "nvidia": "NVIDIA (free tier)",
    "nvidia_ocr": "NVIDIA OCR NIM",
}


def embed(path: Path, max_edge: int = 2000) -> str:
    from PIL import Image

    src = path
    if path.suffix.lower() in {".heic", ".heif"}:
        tmp = Path(tempfile.mkdtemp()) / (path.stem + ".jpg")
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(path), "--out", str(tmp)],
            check=True,
            capture_output=True,
        )
        src = tmp
    img = Image.open(src).convert("RGB")
    if max(img.size) > max_edge:
        scale = max_edge / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    b64 = base64.standard_b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


CSS = """
:root { color-scheme: light dark; --bg:#fff; --fg:#1a1a18; --muted:#6b6b66;
  --line:#e3e1db; --card:#faf9f6; --accent:#8a5a3c; }
@media (prefers-color-scheme: dark) { :root { --bg:#16161a; --fg:#e8e6e1;
  --muted:#96938c; --line:#2e2e34; --card:#1e1e23; --accent:#c99b73; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.6
  ui-sans-serif,-apple-system,system-ui,sans-serif; }
header { padding:14px 20px; border-bottom:1px solid var(--line);
  display:flex; gap:16px; align-items:baseline; flex-wrap:wrap; }
h1 { font-size:16px; margin:0; font-weight:650; }
.hint { color:var(--muted); font-size:13px; }
.page { display:grid; grid-template-columns:minmax(320px,44%) 1fr; gap:0;
  border-bottom:6px solid var(--line); }
@media (max-width:900px) { .page { grid-template-columns:1fr; } }
.photo { position:sticky; top:0; align-self:start; max-height:100vh;
  overflow:auto; padding:16px; border-right:1px solid var(--line); }
.photo img { width:100%; border-radius:6px; display:block; }
.photo h2 { font-size:13px; text-transform:uppercase; letter-spacing:.08em;
  color:var(--muted); margin:0 0 10px; }
.cards { padding:16px; display:flex; flex-direction:column; gap:14px; }
.card { border:1px solid var(--line); border-radius:8px; background:var(--card);
  overflow:hidden; }
.card > summary { cursor:pointer; padding:10px 14px; display:flex;
  gap:10px; align-items:baseline; flex-wrap:wrap; list-style:none; }
.card > summary::-webkit-details-marker { display:none; }
.name { font-weight:650; }
.prov { font-size:11px; text-transform:uppercase; letter-spacing:.07em;
  color:var(--accent); }
.meta { margin-left:auto; color:var(--muted); font-size:12px;
  font-variant-numeric:tabular-nums; }
.body { padding:0 14px 14px; }
pre { white-space:pre-wrap; word-wrap:break-word; margin:0; font:13.5px/1.65
  ui-monospace,SFMono-Regular,Menlo,monospace; }
.err { color:#b4442e; }
@media (prefers-color-scheme: dark) { .err { color:#e08a72; } }
"""


def main() -> int:
    data = json.loads((RESULTS_DIR / "raw.json").read_text())
    by_page: dict[str, list[dict]] = {}
    for r in data:
        by_page.setdefault(r["page"], []).append(r)

    from models import BY_KEY

    parts = [
        "<style>", CSS, "</style>",
        "<header><h1>Handwriting transcription bake-off</h1>",
        '<span class="hint">Read each transcription against the photo. '
        "What counts: cursive accuracy, margin <code>#</code>/<code>##</code> "
        "markers becoming headings, lists preserved, reading order across the "
        "spread, nothing invented or summarised.</span></header>",
    ]

    for page, rows in sorted(by_page.items()):
        src = next(PAGES_DIR.glob(f"{page}.*"), None)
        img = embed(src) if src else ""
        parts += [
            '<section class="page">',
            f'<div class="photo"><h2>{html.escape(page)}</h2>'
            f'<img src="{img}" alt="journal page"></div>',
            '<div class="cards">',
        ]
        for r in sorted(rows, key=lambda x: x["model_key"]):
            m = BY_KEY.get(r["model_key"])
            prov = PROVIDER_LABEL.get(m.provider, "") if m else ""
            if r["error"]:
                meta = "failed"
                body = f'<pre class="err">{html.escape(r["error"])}</pre>'
            else:
                cost = f' · ${r["usd"]:.4f}' if r["usd"] else " · free tier"
                meta = f'{r["seconds"]}s · {r["out_tokens"]} out{cost}'
                body = f'<pre>{html.escape(r["text"].strip())}</pre>'
            parts.append(
                f'<details class="card" open><summary>'
                f'<span class="name">{html.escape(r["model_key"])}</span>'
                f'<span class="prov">{html.escape(prov)}</span>'
                f'<span class="meta">{html.escape(meta)}</span>'
                f"</summary><div class=\"body\">{body}</div></details>"
            )
        parts += ["</div></section>"]

    OUT.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Handwriting bake-off</title></head><body>"
        + "\n".join(parts)
        + "</body></html>"
    )
    print(f"wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
