#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic", "openai", "pillow", "requests"]
# ///
"""Handwriting-transcription bake-off (wayfinder ticket #8).

Runs every journal page in `pages/` through every model in `models.py` and
writes a side-by-side comparison to `results/` for a human to grade.

    export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... NVIDIA_API_KEY=...
    ./bakeoff.py                       # everything
    ./bakeoff.py --only opus-5,gpt-luna
    ./bakeoff.py --pages pages/2026-07-04.jpg
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

from models import BY_KEY, MODELS, Model

HERE = Path(__file__).parent
PAGES_DIR = HERE / "pages"
RESULTS_DIR = HERE / "results"

# The candidate Ingestion prompt. Deliberately phrased against the v0.1 wiki
# model (#6): a Note is the owner's words, faithfully transcribed, never a
# summary of them.
PROMPT = """\
You are transcribing a photographed page from a handwritten personal journal.

Transcribe the page into Markdown, exactly as written. Rules:
- Reproduce the writer's own words verbatim. Do not summarise, correct, \
rephrase, or complete anything.
- Preserve the page's structure. Headings the writer marked with `#` or `##` \
stay Markdown headings; bulleted or numbered lists stay lists; paragraph and \
line breaks are preserved.
- Keep the writer's spelling, punctuation, capitalisation, abbreviations and \
shorthand as-is, including apparent mistakes.
- If a word is genuinely illegible write `[?]`. If you have a confident guess, \
write the guess followed by `[?]` (e.g. `Marcus[?]`).
- Output only the transcription. No preamble, no commentary, no code fence.
"""

# Long edge to downscale to. 2576px is the high-resolution ceiling on current
# Claude models; sending more pixels than that costs tokens and buys nothing.
MAX_EDGE = 2576
MAX_TOKENS = 16000


@dataclass
class Result:
    page: str
    model_key: str
    model_id: str
    text: str = ""
    in_tokens: int = 0
    out_tokens: int = 0
    seconds: float = 0.0
    usd: float = 0.0
    stop_reason: str = ""
    error: str = ""


# --------------------------------------------------------------------------
# image prep
# --------------------------------------------------------------------------


def encode_image(path: Path) -> tuple[str, str]:
    """Return (base64 data, media type), downscaled to MAX_EDGE."""
    from PIL import Image

    src = path
    if path.suffix.lower() in {".heic", ".heif"}:
        # iPhone camera roll. macOS `sips` converts without extra deps.
        if not shutil.which("sips"):
            raise RuntimeError(f"{path.name} is HEIC and `sips` is unavailable")
        tmp = Path(tempfile.mkdtemp()) / (path.stem + ".jpg")
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(path), "--out", str(tmp)],
            check=True,
            capture_output=True,
        )
        src = tmp

    img = Image.open(src)
    img = img.convert("RGB")
    if max(img.size) > MAX_EDGE:
        scale = MAX_EDGE / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.standard_b64encode(buf.getvalue()).decode(), "image/jpeg"


# --------------------------------------------------------------------------
# providers
# --------------------------------------------------------------------------


def run_anthropic(model: Model, b64: str, media_type: str) -> Result:
    import anthropic

    client = anthropic.Anthropic()
    r = Result(page="", model_key=model.key, model_id=model.model_id)
    with client.messages.stream(
        model=model.model_id,
        max_tokens=MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    ) as stream:
        msg = stream.get_final_message()

    if msg.stop_reason == "refusal":
        r.error = f"refusal: {msg.stop_details}"
        return r
    r.text = "".join(b.text for b in msg.content if b.type == "text")
    r.in_tokens = msg.usage.input_tokens
    r.out_tokens = msg.usage.output_tokens
    r.stop_reason = msg.stop_reason or ""
    return r


def run_openai_compat(
    model: Model,
    b64: str,
    media_type: str,
    base_url: str | None,
    api_key: str,
    token_param: str = "max_tokens",
) -> Result:
    """Chat-completions call. Serves OpenAI proper and NVIDIA's compatible API.

    The output-cap parameter differs between them: GPT-5.6 rejects
    `max_tokens` and wants `max_completion_tokens`, while the NVIDIA
    endpoints still take `max_tokens`.
    """
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)
    r = Result(page="", model_key=model.key, model_id=model.model_id)
    resp = client.chat.completions.create(
        model=model.model_id,
        **{token_param: MAX_TOKENS},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )
    r.text = resp.choices[0].message.content or ""
    r.stop_reason = resp.choices[0].finish_reason or ""
    if resp.usage:
        r.in_tokens = resp.usage.prompt_tokens
        r.out_tokens = resp.usage.completion_tokens
    return r


def run_nvidia_ocr(model: Model, b64: str, media_type: str) -> Result:
    """Dedicated OCR NIMs — not chat models, so they take no prompt.

    They live behind the CV endpoint rather than /v1/chat/completions and
    return recognised text plus bounding boxes.
    """
    import requests

    r = Result(page="", model_key=model.key, model_id=model.model_id)
    url = f"https://ai.api.nvidia.com/v1/cv/{model.model_id}"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
            "Accept": "application/json",
        },
        json={
            "input": [
                {"type": "image_url", "url": f"data:{media_type};base64,{b64}"}
            ]
        },
        timeout=300,
    )
    resp.raise_for_status()
    payload = resp.json()
    r.text = _flatten_ocr(payload)
    return r


def _flatten_ocr(payload: dict) -> str:
    """Pull plain text out of an OCR NIM response, shape-tolerantly."""
    out: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for key in ("text", "text_prediction", "content", "markdown"):
                if isinstance(node.get(key), str):
                    out.append(node[key])
                    return
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    return "\n".join(out) if out else json.dumps(payload)[:4000]


DISPATCH = {
    "anthropic": lambda m, b, t: run_anthropic(m, b, t),
    "openai": lambda m, b, t: run_openai_compat(
        m, b, t, None, os.environ["OPENAI_API_KEY"], "max_completion_tokens"
    ),
    "nvidia": lambda m, b, t: run_openai_compat(
        m, b, t, "https://integrate.api.nvidia.com/v1", os.environ["NVIDIA_API_KEY"]
    ),
    "nvidia_ocr": lambda m, b, t: run_nvidia_ocr(m, b, t),
}


def run_one(model: Model, page: Path, b64: str, media_type: str) -> Result:
    started = time.monotonic()
    try:
        r = DISPATCH[model.provider](model, b64, media_type)
    except Exception as exc:  # one model failing must not kill the sweep
        r = Result(page="", model_key=model.key, model_id=model.model_id)
        r.error = f"{type(exc).__name__}: {exc}"[:1500]
    r.page = page.stem
    r.seconds = round(time.monotonic() - started, 1)
    r.usd = round(model.cost(r.in_tokens, r.out_tokens), 5)
    status = "FAIL" if r.error else f"{r.seconds}s ${r.usd:.4f}"
    print(f"  {model.key:<20} {status}", flush=True)
    return r


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------


def merge_prior(results: list[Result]) -> list[Result]:
    """Fold this run into any previous one, keyed by (page, model).

    Without this, `--only gpt-luna` would rewrite raw.json with just that one
    model and silently discard every result already collected. Re-running a
    model replaces its old row; untouched rows survive.
    """
    prior = RESULTS_DIR / "raw.json"
    if not prior.exists():
        return results
    fresh = {(r.page, r.model_key) for r in results}
    kept = [
        Result(**row)
        for row in json.loads(prior.read_text())
        if (row["page"], row["model_key"]) not in fresh
    ]
    if kept:
        print(f"  (carrying forward {len(kept)} result(s) from a previous run)")
    return results + kept


def write_reports(results: list[Result]) -> None:
    raw = RESULTS_DIR / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for r in results:
        (raw / f"{r.page}__{r.model_key}.md").write_text(r.text or r.error)
    (RESULTS_DIR / "raw.json").write_text(
        json.dumps([asdict(r) for r in results], indent=2)
    )

    by_page: dict[str, list[Result]] = {}
    for r in results:
        by_page.setdefault(r.page, []).append(r)

    for page, rows in sorted(by_page.items()):
        src = next((p.name for p in PAGES_DIR.glob(f"{page}.*")), f"{page}.jpg")
        lines = [
            f"# {page} — transcriptions",
            "",
            f"Page photo: [`pages/{src}`](../pages/{src})",
            "",
            "Read each transcription against the photo above and mark it. "
            "What matters: cursive accuracy, structure (`#`/`##`, lists) "
            "preserved, nothing invented, nothing summarised.",
            "",
        ]
        for r in sorted(rows, key=lambda x: x.model_key):
            lines += [
                f"## {r.model_key} (`{r.model_id}`)",
                "",
                f"_{r.seconds}s · {r.in_tokens} in / {r.out_tokens} out · "
                f"${r.usd:.4f} · stop: {r.stop_reason or 'n/a'}_",
                "",
            ]
            if r.error:
                lines += ["```", r.error, "```", ""]
            else:
                lines += [r.text.strip(), "", "---", ""]
        (RESULTS_DIR / f"{page}.md").write_text("\n".join(lines))

    # aggregate table
    agg: dict[str, dict] = {}
    for r in results:
        a = agg.setdefault(
            r.model_key,
            {"pages": 0, "fails": 0, "seconds": 0.0, "usd": 0.0, "out": 0},
        )
        a["pages"] += 1
        a["fails"] += 1 if r.error else 0
        a["seconds"] += r.seconds
        a["usd"] += r.usd
        a["out"] += r.out_tokens

    lines = [
        "# Bake-off summary",
        "",
        "| model | id | pages | failed | avg latency | avg cost/page | $/100 pages |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in MODELS:
        a = agg.get(m.key)
        if not a:
            continue
        n = a["pages"]
        lines.append(
            f"| {m.key} | `{m.model_id}` | {n} | {a['fails']} | "
            f"{a['seconds'] / n:.1f}s | ${a['usd'] / n:.4f} | "
            f"${a['usd'] / n * 100:.2f} |"
        )
    lines += [
        "",
        "NVIDIA build.nvidia.com models show $0.00 — they run on free "
        "rate-limited trial credits, so judge them on fidelity and latency only.",
        "",
    ]
    (RESULTS_DIR / "summary.md").write_text("\n".join(lines))


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated model keys")
    ap.add_argument("--pages", nargs="*", help="specific image paths")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument(
        "--fresh",
        action="store_true",
        help="discard previous results instead of merging into them",
    )
    args = ap.parse_args()

    models = MODELS
    if args.only:
        try:
            models = [BY_KEY[k.strip()] for k in args.only.split(",")]
        except KeyError as exc:
            print(f"unknown model key {exc}; known: {', '.join(BY_KEY)}")
            return 2

    if args.pages:
        pages = [Path(p) for p in args.pages]
    else:
        pages = sorted(
            p
            for p in PAGES_DIR.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".heif"}
        )
    if not pages:
        print(f"no journal photos in {PAGES_DIR}")
        return 1

    needed = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "nvidia_ocr": "NVIDIA_API_KEY",
    }
    missing = {needed[m.provider] for m in models} - set(os.environ)
    if missing:
        print(f"missing env vars: {', '.join(sorted(missing))}")
        return 1

    results: list[Result] = []
    for page in pages:
        print(f"\n{page.name}")
        b64, media_type = encode_image(page)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results += list(
                pool.map(lambda m: run_one(m, page, b64, media_type), models)
            )

    if not args.fresh:
        results = merge_prior(results)
    write_reports(results)
    print(f"\nwrote {RESULTS_DIR}/summary.md and one file per page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
