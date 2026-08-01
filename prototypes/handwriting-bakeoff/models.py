"""Model registry for the handwriting-transcription bake-off.

`usd_in` / `usd_out` are per million tokens. NVIDIA build.nvidia.com endpoints
are free-tier (rate-limited trial credits), so their prices are 0 and the
comparison for them is latency + fidelity only.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    key: str  # short label used in filenames and tables
    provider: str  # anthropic | openai | nvidia | nvidia_ocr
    model_id: str
    usd_in: float = 0.0
    usd_out: float = 0.0
    note: str = ""

    def cost(self, in_tokens: int, out_tokens: int) -> float:
        return (in_tokens * self.usd_in + out_tokens * self.usd_out) / 1_000_000


MODELS: list[Model] = [
    # --- Anthropic -------------------------------------------------------
    Model("opus-5", "anthropic", "claude-opus-5", 5.00, 25.00),
    Model(
        "sonnet-5",
        "anthropic",
        "claude-sonnet-5",
        3.00,
        15.00,
        note="intro pricing $2/$10 through 2026-08-31",
    ),
    # --- OpenAI ----------------------------------------------------------
    Model("gpt-sol", "openai", "gpt-5.6-sol", 5.00, 30.00),
    Model("gpt-terra", "openai", "gpt-5.6-terra", 2.00, 12.00),
    Model("gpt-luna", "openai", "gpt-5.6-luna", 0.20, 1.20),
    # --- NVIDIA build.nvidia.com (OpenAI-compatible chat completions) -----
    Model("inkling", "nvidia", "thinkingmachines/inkling"),
    Model("nemotron-omni", "nvidia", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
    Model("nemotron-vl", "nvidia", "nvidia/nemotron-nano-12b-v2-vl"),
    Model("llama-90b-vl", "nvidia", "meta/llama-3.2-90b-vision-instruct"),
    # `moonshotai/kimi-k2.6` is listed in the NVIDIA catalogue but 404s
    # ("Not found for account") even on a text-only call — not provisioned
    # for this account, so it is out of the sweep rather than failing it.
    # --- NVIDIA dedicated OCR NIMs (not chat models) ---------------------
    Model("nemotron-ocr-v2", "nvidia_ocr", "nvidia/nemotron-ocr-v2"),
    # `nvidia/nemoretriever-ocr-v1` returns 410 Gone — retired, superseded
    # by nemotron-ocr-v2 above.
]

BY_KEY = {m.key: m for m in MODELS}
