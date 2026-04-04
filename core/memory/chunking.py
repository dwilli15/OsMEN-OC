"""Sentence-safe chunking utilities.

These helpers intentionally split text only at sentence boundaries. This avoids
mid-sentence cuts that degrade retrieval quality and downstream generation.
"""

from __future__ import annotations

import re

_URL_PATTERN = re.compile(r"https?://\S+")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")

# Common abbreviation endings that should not trigger sentence splitting.
_ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "etc.",
    "mr.",
    "mrs.",
    "ms.",
    "dr.",
    "prof.",
    "sr.",
    "jr.",
    "u.s.",
)


def _protect_urls(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        value = match.group(0)
        trailing = ""
        if value and value[-1] in ".,!?":
            trailing = value[-1]
            value = value[:-1]
        token = f"__URL_{len(replacements)}__"
        replacements[token] = value
        return f"{token}{trailing}"

    return _URL_PATTERN.sub(_replace, text), replacements


def _restore_tokens(text: str, replacements: dict[str, str]) -> str:
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def split_sentences(text: str) -> list[str]:
    """Split text into sentences without breaking common abbreviations/URLs."""
    normalized = " ".join(text.split())
    if not normalized:
        return []

    protected, url_replacements = _protect_urls(normalized)

    # Shield abbreviation periods so they do not look like sentence boundaries.
    for abbr in _ABBREVIATIONS:
        pattern = re.compile(re.escape(abbr), re.IGNORECASE)

        def _abbr_replace(match: re.Match[str]) -> str:
            return match.group(0).replace(".", "__DOT__")

        protected = pattern.sub(_abbr_replace, protected)

    parts = [p.strip() for p in _SENTENCE_SPLIT_PATTERN.split(protected) if p.strip()]
    restored: list[str] = []
    for part in parts:
        part = part.replace("__DOT__", ".")
        part = _restore_tokens(part, url_replacements)
        restored.append(part)
    return restored


def chunk_text(
    text: str,
    *,
    max_chunk_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[str]:
    """Chunk text at sentence boundaries.

    Token sizes are estimated with a conservative 4 chars/token heuristic.
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    max_chars = max_chunk_tokens * 4
    overlap_chars = overlap_tokens * 4

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence) + (1 if current_sentences else 0)
        if current_sentences and current_len + sentence_len > max_chars:
            chunks.append(" ".join(current_sentences))

            if overlap_chars > 0:
                carry: list[str] = []
                carry_len = 0
                for s in reversed(current_sentences):
                    projected = len(s) + (1 if carry else 0)
                    if carry and carry_len + projected > overlap_chars:
                        break
                    carry.insert(0, s)
                    carry_len += projected
                current_sentences = carry
                current_len = len(" ".join(current_sentences)) if current_sentences else 0
            else:
                current_sentences = []
                current_len = 0

        current_sentences.append(sentence)
        current_len = len(" ".join(current_sentences))

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks
