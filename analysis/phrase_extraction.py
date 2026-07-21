"""
Lightweight seed-phrase extraction from arbitrary page text (used by the
live Search tool when the user pastes a URL or raw content instead of
typing a keyword directly). Deliberately simple frequency counting over
2-4-word windows of non-stopword tokens -- no ML dependency, and auditable
like every other scoring rule in this repo (see analysis/intent_and_audience.py).
"""
import re
from collections import Counter

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "of", "to", "in", "on",
    "at", "for", "with", "by", "from", "up", "about", "into", "over", "after", "is",
    "are", "was", "were", "be", "been", "being", "this", "that", "these", "those",
    "it", "its", "as", "we", "you", "your", "our", "their", "his", "her", "they",
    "he", "she", "not", "no", "yes", "can", "will", "just", "than", "more", "most",
    "also", "all", "each", "any", "such", "there", "here", "what", "which", "who",
    "when", "where", "how", "why", "do", "does", "did", "have", "has", "had", "us",
}

WORD_RE = re.compile(r"[a-zA-Z]+")


def content_words(text):
    return [w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS and len(w) > 1]


def extract_seed_phrases(text, limit=5, min_words=2, max_words=4):
    """Returns up to `limit` candidate seed phrases, most-frequent first,
    each `min_words`-`max_words` tokens long."""
    if not text or not text.strip():
        return []

    words = content_words(text)
    counts = Counter()
    for n in range(min_words, max_words + 1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i + n])
            counts[phrase] += 1

    # Drop phrases that only ever appear as a substring of a more-frequent
    # longer phrase already selected, so the top list isn't dominated by
    # near-duplicates of the same underlying idea.
    ranked = [p for p, _ in counts.most_common(limit * 4)]
    selected = []
    for phrase in ranked:
        if any(phrase in other for other in selected):
            continue
        selected.append(phrase)
        if len(selected) >= limit:
            break
    return selected


def extract_page_text(soup):
    """Given a BeautifulSoup document, pull title/H1/meta-description/body
    text into one string for phrase extraction. Kept separate from the HTTP
    fetch itself so it's unit-testable without a network call."""
    parts = []
    if soup.title and soup.title.string:
        parts.append(soup.title.string)
    for h1 in soup.find_all("h1"):
        parts.append(h1.get_text(" ", strip=True))
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        parts.append(meta_desc["content"])
    for p in soup.find_all(["p", "li"])[:80]:
        parts.append(p.get_text(" ", strip=True))
    return " ".join(parts)
