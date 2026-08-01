# Handwriting-transcription bake-off

Prototype for [#8](https://github.com/mcnewcp/personal-assistant/issues/8) — can
current vision models transcribe the journal reliably enough for Ingestion?

## Running it

```sh
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... NVIDIA_API_KEY=...
./bakeoff.py                      # every model × every page in pages/
./bakeoff.py --only sonnet-5      # subset
./report.py                       # → results/compare.html
open results/compare.html
```

`pages/` and `results/` are both gitignored. Journal photos and their
transcriptions never enter the repo — the camera roll is the archive of record
([#6](https://github.com/mcnewcp/personal-assistant/issues/6)), and
`compare.html` embeds the photo so it stays a local file. Nothing is uploaded
anywhere except to the model APIs being tested.

## Method

Each page goes to every model in `models.py` as a single image plus the
candidate Ingestion prompt in `bakeoff.py`. That prompt is written against the
Note definition from #6 — verbatim words, structure preserved, `[?]` for
illegible, explicitly no summarising — so the bake-off tests the prompt as
much as the models.

Images are downscaled to 2576px on the long edge (the high-resolution ceiling
on current Claude models; more pixels cost tokens and buy nothing) and HEIC is
converted via `sips`, so camera-roll files work unmodified.

Cost is computed from returned token usage, not from the published price
sheet. Per-model failures are captured rather than raised, so one dead
endpoint doesn't abort a sweep.

## What the pages test

Both sample pages are **two-page spreads**, and the `#` / `##` markers are
written in the **left margin** rather than inline. So a model has to (a) read
cursive, (b) get reading order right across two pages, and (c) map a marginal
marker onto the adjacent line as a Markdown heading. (c) turned out to be the
sharpest discriminator.

## Models that couldn't be tested

| model | why |
| --- | --- |
| `gpt-5.6-sol` / `-terra` / `-luna` | 429 `credit_balance_exhausted` — OpenAI account has no credits |
| `moonshotai/kimi-k2.6` | 404 "Not found for account" even on a text-only call — listed in NVIDIA's catalogue but not provisioned |
| `nvidia/nemoretriever-ocr-v1` | 410 Gone — retired, superseded by `nemotron-ocr-v2` |

## Caveats

- Two pages, one writer, one session. This sizes the gap between tiers; it is
  not an error-rate measurement.
- Re-running the same model on the same page gives slightly different output
  (strikethrough handling drifted between two `opus-5` runs), so treat small
  differences between adjacent models as noise.
- Anthropic models ran at default effort with thinking on, which is what a
  naive integration would do. Lower effort would cut cost and is untested.
