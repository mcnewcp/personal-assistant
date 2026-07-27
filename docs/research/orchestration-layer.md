# Choosing the LLM Orchestration Layer

**Date:** 2026-07-27
**Issue:** "Choose the LLM orchestration layer" (mcnewcp/personal-assistant)

## The question

For a small Python CLI pipeline (v0.1 scale, single developer) that (a) transcribes handwritten journal photos — so vision/multimodal input is required — and (b) maintains a Markdown wiki in an Obsidian vault, which orchestration layer should we use?

1. **pydantic-ai** (Pydantic AI, by the Pydantic team)
2. **LangGraph** (LangChain's graph orchestration library)
3. **Raw provider SDK** (anthropic and/or openai Python SDKs behind a thin in-house interface)

All claims below were checked against primary sources (official docs, PyPI, GitHub releases) as of 2026-07-27. Items I could not fully verify are flagged inline.

---

## Summary and recommendation

**Recommendation: pydantic-ai (installed as `pydantic-ai-slim[anthropic]`, adding provider extras only as needed).**

Rationale in one paragraph: the pipeline is linear (photo → transcription → structured extraction → Markdown writes), which means the orchestration layer's job is mostly (1) typed structured outputs with validation/retry, (2) clean image input, (3) easy provider swapping, and (4) testability. pydantic-ai is the best fit on all four: `output_type=<PydanticModel>` with automatic validation and `ModelRetry` ([output docs](https://pydantic.dev/docs/ai/core-concepts/output/)), first-class `BinaryContent`/`ImageUrl` image input ([input docs](https://pydantic.dev/docs/ai/advanced-features/input/)), provider swap via a `'provider:model'` string ([models docs](https://pydantic.dev/docs/ai/models/)), and purpose-built test doubles (`TestModel`, `FunctionModel`, `Agent.override`, `ALLOW_MODEL_REQUESTS=False`) ([testing docs](https://pydantic.dev/docs/ai/guides/testing/)). Its telemetry is strictly opt-in — "if the `logfire` package is installed and configured and agent instrumentation is enabled then detailed information about agent runs is sent to Logfire. Otherwise there's virtually no overhead and nothing is sent" ([Logfire integration docs](https://pydantic.dev/docs/ai/integrations/logfire/)) — which matters given personal journal content flows through the pipeline.

**Key trade-offs accepted:**

- pydantic-ai moves *fast* — near-daily minor releases in July 2026 (v2.10.0 → v2.18.0 between Jul 14 and Jul 24, per [GitHub releases](https://github.com/pydantic/pydantic-ai/releases)). Pin the version and upgrade deliberately.
- It is one more dependency layer than the raw SDK; the "agent" abstraction is slightly more than a linear pipeline strictly needs.
- LangGraph's real strengths (durable stateful graphs, checkpointing, human-in-the-loop) are unused at this scale, and its ecosystem's gravitational pull toward LangSmith is an unwanted default posture for private journal data (even though tracing is verifiably opt-in).

**What would trigger revisiting:**

- The pipeline becomes a genuinely stateful, long-running, branching agent (resumable runs, human-in-the-loop review queues, parallel fan-out) → re-evaluate LangGraph.
- We commit permanently to a single provider and want minimum dependencies → collapse to the raw `anthropic` SDK behind the thin interface we'd already have via pydantic-ai's model seam.
- pydantic-ai's release churn produces repeated breaking changes in APIs we use (a 3.x with heavy migration cost), or the project's direction ties core features to Logfire.

---

## Comparison at a glance

| Axis | pydantic-ai | LangGraph | Raw SDK + thin wrapper |
|---|---|---|---|
| Current stable (verified) | 2.18.0 (2026-07-24) | 1.2.9 (2026-07-10) | anthropic 0.120.0 (2026-07-24); openai 2.48.0 |
| Release cadence | Near-daily minors | Every ~3–7 days | ~Weekly |
| Boilerplate for linear pipeline | Low (one `Agent` per step) | Medium (StateGraph/nodes/edges, or `create_agent`) | Lowest per-call, but you write the seam yourself |
| Provider swap | `'anthropic:…'` → `'openai:…'` string | `init_chat_model("provider:model")` + per-provider package | Rewrite call sites, or OpenAI-compat endpoints / LiteLLM |
| Pydantic-typed output | Native (`output_type`), 3 modes, `ModelRetry` | `response_format` / `ToolStrategy` / `ProviderStrategy`, retry via `handle_errors` | Native per SDK (`messages.parse`, `responses.parse`), no cross-provider retry loop |
| Image input | `BinaryContent(data, media_type)` — provider-agnostic | Standard content blocks (`{"type":"image","base64":…,"mime_type":…}`) | Provider-specific block shapes (you normalize) |
| Test doubles | `TestModel`, `FunctionModel`, `Agent.override`, request kill-switch | `GenericFakeChatModel`, `InMemorySaver`; nodes are plain functions | `respx`/mock the client or fake your own interface |
| Telemetry default | Nothing sent; opt-in Logfire/OTel | Nothing sent; opt-in LangSmith via env vars | None exists |

---

## Axis 1: Complexity vs benefit at v0.1 scale

**pydantic-ai.** Latest stable **2.18.0**, released 2026-07-24 ([PyPI](https://pypi.org/project/pydantic-ai/), [GitHub releases](https://github.com/pydantic/pydantic-ai/releases)); Python ≥ 3.10. Cadence is very fast: eight minor releases in the ten days before this research (2.10.0 on Jul 14 → 2.18.0 on Jul 24). The `pydantic-ai` metapackage is heavy — it depends on `pydantic-ai-slim[anthropic,cli,evals,google,logfire,mcp,openai,retries,web]` (per PyPI metadata), i.e. it drags in the Logfire SDK, MCP, evals, and a CLI. The intended lean path is **`pydantic-ai-slim`** with only the extras you need, e.g. `pydantic-ai-slim[anthropic]` ([install docs](https://pydantic.dev/docs/ai/install/)). Boilerplate for a linear pipeline is small: each step is an `Agent(model, output_type=SomeModel)` and a `run_sync()` call — no graph, no runtime. Learning curve is low if you already know Pydantic (this project does — Pydantic models are the natural shape for the extraction step).

**LangGraph.** Latest stable **1.2.9**, released 2026-07-10 ([PyPI](https://pypi.org/project/langgraph/), [GitHub releases](https://github.com/langchain-ai/langgraph/releases)); releases land every ~3–7 days. (I did not verify the exact 1.0 GA date on the releases page — only 1.2.4+ was visible.) Python ≥ 3.10. Dependencies: `langchain-core`, `langgraph-checkpoint`, `langgraph-prebuilt`, `langgraph-sdk`, `pydantic`, `xxhash` (PyPI metadata) — plus a per-provider package (`langchain-anthropic`, `langchain-openai`, …) for actual model calls. LangGraph self-describes as "a low-level orchestration framework and runtime for building, managing, and deploying long-running, stateful agents" ([overview](https://docs.langchain.com/oss/python/langgraph/overview)); the docs note you don't need LangChain proper, but model/tool integration in practice comes from LangChain packages. For a linear 3-step pipeline you'd either define a `StateGraph` with nodes/edges (concepts: state schema, reducers, checkpointers) or use `create_agent` — either way you're learning a graph runtime whose payoff (durable execution, interrupts, branching) this pipeline doesn't use at v0.1.

**Raw SDK.** `anthropic` **0.120.0** (2026-07-24) and `openai` **2.48.0**, both verified on PyPI; both release roughly weekly. Smallest footprint: the anthropic SDK's deps are just `httpx`, `pydantic`, `anyio`, `jiter`, `distro`, `docstring-parser`, `sniffio`, `typing-extensions` (PyPI metadata). Per-call boilerplate is minimal and both SDKs natively accept/return Pydantic (see Axis 3). The hidden cost is the thin interface itself: to keep call sites provider-neutral you must design and maintain your own abstraction for message shapes, image blocks, structured-output mechanics, error taxonomies, and retries — exactly the seam pydantic-ai already ships and tests.

**Verdict:** raw SDK is simplest for one provider forever; pydantic-ai is simplest if you want the provider/testing seam without writing it; LangGraph buys machinery this pipeline doesn't need yet.

## Axis 2: Provider-agnosticism

**pydantic-ai.** Models are specified as `'provider:model'` strings (`'anthropic:claude-sonnet-4-5'`, `'openai:gpt-5.2'`, Google via `google-gla:`/`google-vertex:`); the framework resolves the right Model class, Provider (auth/endpoint), and Profile (request-shaping) automatically, so swapping is a one-string change ([models docs](https://pydantic.dev/docs/ai/models/)). Built-in support covers OpenAI, Anthropic, Google, Bedrock, Groq, Mistral, Cohere, xAI, Hugging Face and more, plus any OpenAI-compatible endpoint via `OpenAIChatModel` with a custom provider (Ollama, DeepSeek, Azure, etc.). `FallbackModel` gives automatic failover between models. This is the strongest abstraction of the three for the "swap Anthropic/OpenAI/Google" requirement.

**LangGraph.** Provider abstraction comes from LangChain's `init_chat_model("provider:model")`; "each provider package implements the same standard interface, so you can swap providers without rewriting application logic," and new model names pass straight through to the provider API ([models docs](https://docs.langchain.com/oss/python/langchain/models)). You must install the matching integration package per provider (`langchain-anthropic`, `langchain-openai`, `langchain-google-genai`). Effectively equivalent to pydantic-ai in swap ergonomics, at the cost of an extra package per provider.

**Raw SDK.** No abstraction — the anthropic and openai SDKs have different clients, message/content-block shapes, structured-output mechanics, and error classes. A thin in-house interface must cover at minimum: client construction/auth, a common message + image-content representation, structured-output invocation (Anthropic `output_config.format` / `messages.parse` vs OpenAI `responses.parse`/`text_format`), response unwrapping, error mapping (rate limits/retryable vs not), and streaming if ever needed. Two routes reduce this work:
- **OpenAI-compatible endpoints:** Google's Gemini API officially exposes an OpenAI-compatible endpoint ([Google docs](https://ai.google.dev/gemini-api/docs/openai)), and Anthropic documents an OpenAI SDK compatibility layer ([Anthropic docs](https://platform.claude.com/docs/en/api/openai-sdk); *listed in Anthropic's docs but I did not re-verify its current feature coverage*). Writing the wrapper once against the `openai` SDK + `base_url` gets you multi-provider text calls, but compat layers historically lag on provider-specific features (fine-grained image controls, strict structured outputs, thinking parameters), so this weakens exactly the features this pipeline relies on.
- **LiteLLM:** an "open-source library that gives you a single, unified interface to call 100+ LLMs" via `litellm.completion("anthropic/…")` returning OpenAI-format responses ([LiteLLM docs](https://docs.litellm.ai/docs/)). It changes the calculus by making the thin wrapper mostly unnecessary — but then you've adopted a third-party abstraction layer anyway, at which point pydantic-ai gives you more (typed outputs, testing) for the same dependency budget.

**Verdict:** pydantic-ai and LangGraph both make provider swap a string change; raw SDK requires either committing to one provider or building/borrowing an abstraction.

## Axis 3: Typed / structured outputs

**pydantic-ai.** The core feature. `Agent(..., output_type=MyModel)` accepts Pydantic models, dataclasses, unions, and output functions; outputs are schema-built and validated by Pydantic automatically. Three delivery modes: **Tool Output** (default — schema presented as a special output tool; works on virtually all models), **Native Output** (provider structured-output feature), **Prompted Output** (schema injected into instructions), selectable via `ToolOutput`/`NativeOutput`/`PromptedOutput` markers. Validation failures and `@agent.output_validator` functions can raise `ModelRetry` to send errors back to the model, budgeted via `Agent(retries={'output': N})` ([output docs](https://pydantic.dev/docs/ai/core-concepts/output/)). This retry-on-validation-failure loop is exactly what the "structured extraction" step wants and is the thing you'd otherwise hand-roll.

**LangGraph/LangChain.** `create_agent(..., response_format=MyModel)` supports Pydantic `BaseModel` (returns validated instances), dataclasses, `TypedDict`, and raw JSON schema. Strategy is auto-selected: `ProviderStrategy` uses native provider structured outputs (OpenAI/Anthropic/xAI) for "high reliability and strict validation"; `ToolStrategy` falls back to tool-calling for other models, with `handle_errors=True` (default) catching validation errors and automatically retrying with feedback ([structured output docs](https://docs.langchain.com/oss/python/langchain/structured-output)). Result lands in state under `structured_response`. Solid, roughly at parity with pydantic-ai, though validation/retry knobs are on the agent wrapper rather than woven through a validator-function system.

**Raw SDK.** Both SDKs now have first-class Pydantic support, so this axis is *not* a strong differentiator per-call:
- **Anthropic:** `client.messages.parse(..., output_format=MyModel)` returns a validated instance on `response.parsed_output`; the canonical API-level mechanism is `output_config={"format": {"type": "json_schema", "schema": …}}` on `messages.create` (the old top-level `output_format` request param is deprecated), plus `strict: true` tool use for validated tool params ([structured outputs docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)).
- **OpenAI:** `client.responses.parse(..., text_format=MyModel)` (Responses API, current) or `chat.completions.parse(..., response_format=MyModel)` (legacy), with strict JSON-schema enforcement; parsed objects on `.output_parsed`/`.parsed` ([structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)).

What you don't get is a provider-neutral retry-on-validation loop or a uniform way to express "this Pydantic model, on any provider" — that's wrapper work.

**Verdict:** all three can produce validated Pydantic objects; pydantic-ai has the richest validation/retry semantics and keeps them provider-neutral.

## Axis 4: Vision / multimodal support

**pydantic-ai.** Images are passed inline in the prompt list: `agent.run_sync(['Transcribe this page', BinaryContent(data=Path('page.jpg').read_bytes(), media_type='image/jpeg')])`, or `ImageUrl(url=…)` for remote images (with `force_download=True` to fetch locally first). The framework adapts per provider — e.g. it sends URLs directly to OpenAI but downloads and sends bytes to Anthropic ([input docs](https://pydantic.dev/docs/ai/advanced-features/input/)). Local-file bytes via `BinaryContent` is precisely the journal-photo case. Docs caveat that image support varies by model — true of every option here.

**LangGraph/LangChain.** LangChain 1.x standard content blocks: `{"type": "image", "base64": <data>, "mime_type": "image/jpeg"}` or `{"type": "image", "url": …}` inside a message's content list, documented as "a standard representation for message content that works across providers," with provider-specific extras nestable under `"extras"` ([messages docs](https://docs.langchain.com/oss/python/langchain/messages)). Works fine; slightly more dict-shaped than pydantic-ai's typed objects.

**Raw SDK.** Fully supported but provider-specific:
- **Anthropic:** image content blocks with `source: {type: "base64", media_type: "image/png", data: …}` or `{type: "url", url: …}`; supported formats JPEG/PNG/GIF/WebP ([vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)). The Files API (beta) allows upload-once/reference-by-id.
- **OpenAI:** `input_image` content parts with an `image_url` (remote URL or base64 data URL) in the Responses API ([images & vision guide](https://developers.openai.com/api/docs/guides/images-vision); *shape not re-verified in this pass — flagged*).
Your thin interface must normalize these two block shapes — mechanical but real work, and a place where provider differences leak.

**Verdict:** all three handle local image bytes; pydantic-ai's `BinaryContent` is the cleanest single API for it.

## Axis 5: Testability in pytest

**pydantic-ai.** The standout. Official, documented test utilities ([testing docs](https://pydantic.dev/docs/ai/guides/testing/)):
- `TestModel` — generates schema-valid structured data for tools and `output_type` with no LLM call, so extraction-step plumbing tests are nearly free.
- `FunctionModel` — you write a function receiving the message history and returning the model response, for scripted behaviors.
- `Agent.override(model=…)` — context manager to swap the model/deps without touching call sites (ideal as a pytest fixture).
- `models.ALLOW_MODEL_REQUESTS = False` — global kill-switch so no test can accidentally hit a real API.
- `capture_run_messages()` — assert on the exact request/response exchange.
Dependency injection is also first-class via the agent `deps` system.

**LangGraph.** Official unit-testing docs recommend `GenericFakeChatModel` (from `langchain_core.language_models.fake_chat_models`) — "script exact responses (text, tool calls, and errors) so tests are fast, free, and repeatable without API keys" — plus `InMemorySaver` for multi-turn state tests ([unit-testing docs](https://docs.langchain.com/oss/python/langchain/test/unit-testing)). Because nodes are plain Python functions taking state, they're independently unit-testable. Workable, but the fake model returns scripted messages — nothing auto-generates schema-valid structured outputs the way `TestModel` does, and there's no built-in "block real requests" guard.

**Raw SDK.** No official test doubles from either vendor. Standard practice: mock at the HTTP layer (`respx` for the SDKs' httpx transport) or, better, define your own thin interface (protocol/ABC) and inject a fake in tests — i.e., the testability story is only as good as the wrapper you design. That's fine, but it's an in-house maintenance obligation, and mocking the SDK's response objects (typed content-block unions) is fiddlier than it looks.

**Verdict:** pydantic-ai > LangGraph > raw SDK, unless you invest in a well-designed in-house seam.

## Axis 6: Data-handling / telemetry posture

This matters here: personal journal content flows through every step. (The model provider sees the data regardless; this axis is about the *framework* layer.)

**pydantic-ai.** Strictly opt-in, verified: "Pydantic AI has built-in (but optional) support for Logfire… if the `logfire` package is installed and configured and agent instrumentation is enabled then detailed information about agent runs is sent to Logfire. Otherwise there's virtually no overhead and nothing is sent." Enabling requires all of: installing the `logfire` extra, `logfire.configure()`, and `logfire.instrument_pydantic_ai()` (or `Agent(instrument=True)`/`Agent.instrument_all()`) ([Logfire integration docs](https://pydantic.dev/docs/ai/integrations/logfire/)). Instrumentation is OpenTelemetry-based, so you can point it at any OTel backend (or self-host) with `logfire.configure(send_to_logfire=False)` + `OTEL_EXPORTER_OTLP_ENDPOINT` — the docs list 14+ alternative backends. Docs stance: Logfire is prominently marketed (and the fat `pydantic-ai` metapackage installs the Logfire SDK — another reason to use `pydantic-ai-slim`), but the default behavior is verifiably "send nothing." Practical hardening for this project: use `-slim` without the `logfire` extra, so the export path isn't even installed.

**LangGraph.** Also strictly opt-in, verified: tracing to LangSmith requires `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY`; "without these variables configured, no tracing occurs automatically" ([LangSmith tracing docs](https://docs.langchain.com/langsmith/trace-with-langchain)). Docs stance: the LangChain ecosystem markets LangSmith aggressively (observability, evals, deployment are all LangSmith-branded), and the enable path is *ambient* — a stray `LANGSMITH_TRACING=true` in a shell profile silently ships prompt/response payloads (i.e., journal text) to the hosted platform, since instrumentation is built into `langchain-core`. Opt-in, but the footgun surface is env-var-shaped rather than code-shaped.

**Raw SDK.** No framework telemetry exists at all — the anthropic/openai SDKs send requests to the provider API and nothing else. Zero additional trust surface; the strongest posture on this axis by construction.

**Verdict:** raw SDK is trivially safest; pydantic-ai (slim, no logfire extra) is effectively equivalent in practice; LangGraph is opt-in but its ecosystem defaults and env-var activation deserve a guardrail (e.g., assert `LANGSMITH_TRACING` unset at startup) if chosen.

---

## Per-option detail

### Option 1: pydantic-ai — **recommended**

- **Install:** `pydantic-ai-slim[anthropic]` (add `openai`/`google` extras when swapping). Avoid the fat metapackage (pulls logfire/mcp/evals/cli/web). Python ≥ 3.10. Version 2.18.0 as of 2026-07-24.
- **Pipeline shape:** one `Agent` per step. Transcription: `Agent('anthropic:<model>', output_type=str \| TranscriptModel)` called with `[prompt, BinaryContent(photo_bytes, media_type='image/jpeg')]`. Extraction: `Agent(..., output_type=JournalEntry)` with `@output_validator`s raising `ModelRetry` for semantic checks. Markdown writes stay plain Python — no need to model them as tools.
- **Risks:** rapid release cadence (pin + lockfile; the 1.x→2.x major happened within the last year); framework surface larger than strictly needed; docs URLs recently migrated from ai.pydantic.dev to pydantic.dev/docs/ai (both resolve).

### Option 2: LangGraph — not recommended at v0.1

- Strong, stable (1.2.x) graph runtime with real differentiators — checkpointing/durable execution, interrupts, human-in-the-loop, streaming — none of which a linear CLI pipeline uses. Costs: graph concepts to learn, `langchain-core` + per-provider packages, weaker structured-output/test ergonomics than pydantic-ai, and an ecosystem posture oriented toward hosted LangSmith. Reconsider if the assistant grows into a long-running stateful agent with review/approval loops.

### Option 3: Raw SDK behind a thin interface — credible runner-up

- Best dependency and privacy posture; both SDKs natively parse into Pydantic models and handle images well. The cost is owning the abstraction: provider-neutral message/image shapes, structured-output invocation differences, validation-retry loops, error taxonomy, and test fakes. At v0.1 with one developer, that's a real fraction of the project's total code. The OpenAI-compatible-endpoint route (or LiteLLM) reduces the wrapper burden but reintroduces a third-party layer or a lowest-common-denominator feature set — at which point pydantic-ai's richer, typed layer is the better spend of the same complexity budget.
- Choose this if the project decides to hard-commit to Anthropic-only (or OpenAI-only) and values minimum moving parts over swap-ability.

---

## Sources

**pydantic-ai (primary):**
- PyPI metadata (version 2.18.0, deps): https://pypi.org/project/pydantic-ai/
- GitHub releases (dates/cadence): https://github.com/pydantic/pydantic-ai/releases
- Install / slim + extras: https://pydantic.dev/docs/ai/install/
- Models & providers / FallbackModel: https://pydantic.dev/docs/ai/models/
- Structured output / ModelRetry / output modes: https://pydantic.dev/docs/ai/core-concepts/output/
- Image & multimodal input (ImageUrl, BinaryContent): https://pydantic.dev/docs/ai/advanced-features/input/
- Testing (TestModel, FunctionModel, Agent.override, ALLOW_MODEL_REQUESTS): https://pydantic.dev/docs/ai/guides/testing/
- Logfire/OTel integration & opt-in stance: https://pydantic.dev/docs/ai/integrations/logfire/

**LangGraph / LangChain (primary):**
- PyPI metadata (version 1.2.9, deps): https://pypi.org/project/langgraph/
- GitHub releases (dates/cadence): https://github.com/langchain-ai/langgraph/releases
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- Models / init_chat_model: https://docs.langchain.com/oss/python/langchain/models
- Structured output (ToolStrategy/ProviderStrategy/handle_errors): https://docs.langchain.com/oss/python/langchain/structured-output
- Messages / image content blocks: https://docs.langchain.com/oss/python/langchain/messages
- Unit testing (GenericFakeChatModel, InMemorySaver): https://docs.langchain.com/oss/python/langchain/test/unit-testing
- LangSmith tracing env vars (opt-in): https://docs.langchain.com/langsmith/trace-with-langchain

**Provider SDKs (primary):**
- anthropic PyPI (0.120.0, 2026-07-24, deps): https://pypi.org/project/anthropic/
- openai PyPI (2.48.0, deps): https://pypi.org/project/openai/
- Anthropic structured outputs (`messages.parse`, `output_config.format`, strict tools): https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Anthropic vision (base64/URL image blocks): https://platform.claude.com/docs/en/build-with-claude/vision
- OpenAI structured outputs (`responses.parse`, `text_format`, strict mode): https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI images & vision guide (*shape not re-verified this pass*): https://developers.openai.com/api/docs/guides/images-vision
- Anthropic OpenAI SDK compatibility layer (*coverage not re-verified this pass*): https://platform.claude.com/docs/en/api/openai-sdk
- Google Gemini OpenAI-compatible endpoint: https://ai.google.dev/gemini-api/docs/openai

**Other:**
- LiteLLM (unified 100+ provider interface): https://docs.litellm.ai/docs/

**Verification notes:** version numbers, release dates, telemetry defaults, and API mechanics above were checked against the sources listed on 2026-07-27. Items explicitly *not* re-verified as current: LangGraph 1.0's original GA date; the exact current feature coverage of Anthropic's OpenAI-compat layer; the precise OpenAI Responses-API image block field names; LiteLLM's vision/structured-output coverage (its unified-interface claim was verified, feature depth was not).
