"""
Live Search tool only: uses Claude (the official `anthropic` Python SDK) to
turn a seed keyword / URL / pasted content into a list of candidate keyword
PHRASES the way an experienced Ayurveda-hospital marketing strategist would
-- semantic expansion, synonyms, question variations, long-tail ideas --
not the mechanical n-gram frequency counting in analysis/phrase_extraction.py.

Deliberate boundary: this module only proposes candidate keyword STRINGS.
Every score on those keywords (intent, compliance, AEO, confidence, ...)
still comes from this repo's own deterministic analysis/ pipeline via
analysis/entry_builder.py -- never from the model. That keeps scoring
auditable and identical between the live search and the weekly batch build,
and it's why this module has no dependency on entry_builder at all.

The system prompt is brand-specific (config.BrandConfig.ai_system_prompt)
-- each brand (Healing Village, Villaraag, ...) gets its own persona/
business-context/compliance framing, passed in by the caller rather than
hardcoded here.

Needs ANTHROPIC_API_KEY in Vercel's environment -- separate from
SEMRUSH_API_KEY, and separate from any Claude Code/Claude.ai subscription
(this is pay-as-you-go Claude API billing, from console.anthropic.com).
Uses claude-opus-4-8 with structured output (Pydantic schema via
client.messages.parse), no extended thinking (a keyword-brainstorm task
doesn't need multi-step reasoning, and skipping it keeps latency/cost down).
Rough cost: ~$0.01-0.02 per search at Opus rates ($5/$25 per MTok).

Raises RuntimeError if the key is unset or the call fails -- callers (see
api/search.py) should catch this and fall back to the simpler regex-based
analysis/phrase_extraction.py path rather than failing the whole search.
"""
import os

from pydantic import BaseModel

MODEL = "claude-opus-4-8"
MAX_INPUT_CHARS = 4000
MAX_KEYWORDS = 25


class KeywordIdeas(BaseModel):
    keywords: list[str]


def suggest_keywords(seed_text, brand):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=brand.ai_system_prompt,
        messages=[{"role": "user", "content": seed_text[:MAX_INPUT_CHARS]}],
        output_format=KeywordIdeas,
    )
    return normalize_keywords(response.parsed_output.keywords)


def normalize_keywords(raw_keywords):
    seen = set()
    result = []
    for k in raw_keywords:
        kw = k.strip().lower()
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)
        if len(result) >= MAX_KEYWORDS:
            break
    return result


def build_input_text(seed_keyword, resolved_text):
    parts = []
    if seed_keyword:
        parts.append(f"Seed keyword/service: {seed_keyword}")
    if resolved_text:
        parts.append(f"Page content:\n{resolved_text[:3000]}")
    return "\n\n".join(parts)
