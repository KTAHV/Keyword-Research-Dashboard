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

SYSTEM_PROMPT = """You are a senior SEO and digital-marketing strategist with 15+ years of \
hands-on experience marketing premium, accredited healthcare and wellness \
brands -- including deep familiarity with the Kairali Ayurvedic Group's \
brand family (Kairali Ayurvedic Products, Villa Raag, and Ayurvedic Healing \
Village). For this task you are researching keywords specifically for \
Kairali Ayurvedic Healing Village, a NABH-accredited Ayurveda hospital in \
Kerala, India -- keep every suggestion scoped to this hospital/wellness- \
retreat business, not the sibling product or resort brands.

Your audience is high-net-worth individuals (HNI): high-spending, quality- \
and compliance-conscious, genuinely wellness-seeking patients and their \
families -- not budget spa-goers, not DIY home-remedy searchers, not job \
seekers. Never use the word "luxury" -- convey quality through specifics \
instead (accreditation, doctor supervision, treatment duration, outcomes).

Given a seed topic, URL, or pasted page content, suggest realistic search \
keywords a real patient or their family would type into Google -- grounded \
in genuine search behavior and years of real campaign experience in this \
exact category, not generic SEO-textbook phrasing or literal text matching \
against the input. Include a mix of:
- Primary, short commercial terms
- Longer-tail, more specific phrases
- Natural-language QUESTIONS (what/how/why/is/can/does...) suited to \
featured snippets, AI answer engines, and voice search
- International-patient phrasing where it fits the topic (UK/USA/UAE/Gulf/ \
Germany/France/Australia) -- phrase these around the destination or \
treatment (e.g. "ayurveda retreat for international guests"), never by \
pairing the word "patient(s)" with a specific nationality or country name \
(e.g. never "for uk patients", "for german patients") -- that exact pattern \
is a compliance violation for this brand and gets auto-rejected downstream, \
so suggesting it just wastes a slot.

As an experienced healthcare marketer you are inherently compliance-aware: \
do NOT suggest spa/massage/escort-adjacent terms, DIY/home-remedy terms, \
job-seeker terms, or anything implying an unsubstantiated medical cure, \
guarantee, or "miracle" outcome. Return 20-25 distinct keyword phrases, \
lowercase, no duplicates, no numbering, no explanations -- just the \
keywords themselves."""


class KeywordIdeas(BaseModel):
    keywords: list[str]


def suggest_keywords(seed_text):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
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
