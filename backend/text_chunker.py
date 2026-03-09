"""
Text chunker for splitting research papers into semantic chunks.
Produces overlapping chunks of roughly target word count for embedding and retrieval.
"""

import re
from typing import List, Optional

from config import ChunkerConfig


class TextChunker:
    """
    Splits long text into overlapping chunks suitable for embedding and FAISS retrieval.
    Tries to break at paragraph/sentence boundaries when possible.
    """

    def __init__(self, config: Optional[ChunkerConfig] = None):
        """
        Initialize the chunker with optional config.

        Args:
            config: ChunkerConfig instance. Uses default if not provided.
        """
        self.config = config or ChunkerConfig()
        self.target = self.config.TARGET_CHUNK_WORDS
        self.overlap = self.config.OVERLAP_WORDS
        self.min_chunk = self.config.MIN_CHUNK_WORDS
        self.max_chunk = self.config.MAX_CHUNK_WORDS

    def _word_count(self, text: str) -> int:
        """Return number of words in text."""
        return len(text.split())

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (simple regex)."""
        if not text.strip():
            return []
        # Split on sentence-ending punctuation followed by space or end
        parts = re.split(r'(?<=[.!?])\s+', text)
        return [p.strip() for p in parts if p.strip()]

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs by double newlines."""
        if not text.strip():
            return []
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Build chunks by grouping paragraphs. Each chunk aims for target word count.

        Args:
            text: Full document text.

        Returns:
            List of text chunks.
        """
        paragraphs = self._split_into_paragraphs(text)
        if not paragraphs:
            return self.chunk_by_sentences(text)

        chunks = []
        current = []
        current_words = 0

        for para in paragraphs:
            para_words = self._word_count(para)
            if current_words + para_words > self.max_chunk and current:
                chunk_text = "\n\n".join(current)
                chunks.append(chunk_text)
                # Overlap: keep last paragraphs that fit in overlap words
                overlap_words = 0
                new_current = []
                for p in reversed(current):
                    w = self._word_count(p)
                    if overlap_words + w <= self.overlap:
                        new_current.insert(0, p)
                        overlap_words += w
                    else:
                        break
                current = new_current
                current_words = sum(self._word_count(p) for p in current)
            current.append(para)
            current_words += para_words

        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def chunk_by_sentences(self, text: str) -> List[str]:
        """
        Fallback: build chunks by grouping sentences to target word count.

        Args:
            text: Full document text.

        Returns:
            List of text chunks.
        """
        sentences = self._split_into_sentences(text)
        if not sentences:
            # Last resort: split by raw word count
            words = text.split()
            chunks = []
            i = 0
            while i < len(words):
                end = min(i + self.target, len(words))
                chunk_words = words[i:end]
                # Add overlap for next start
                overlap_end = min(end + self.overlap, len(words))
                i = max(end - self.overlap, end)
                if i >= len(words):
                    break
                chunks.append(" ".join(chunk_words))
            if words:
                chunks.append(" ".join(words[i:]))
            return [c for c in chunks if c.strip()]
        chunks = []
        current = []
        current_words = 0
        for sent in sentences:
            w = self._word_count(sent)
            if current_words + w > self.max_chunk and current:
                chunk_text = " ".join(current)
                chunks.append(chunk_text)
                # Overlap
                overlap_words = 0
                new_current = []
                for s in reversed(current):
                    sw = self._word_count(s)
                    if overlap_words + sw <= self.overlap:
                        new_current.insert(0, s)
                        overlap_words += sw
                    else:
                        break
                current = new_current
                current_words = sum(self._word_count(s) for s in current)
            current.append(sent)
            current_words += w
        if current:
            chunks.append(" ".join(current))
        return chunks

    def chunk(self, text: str) -> List[str]:
        """
        Split text into semantic chunks (paragraph-first, then sentence fallback).

        Args:
            text: Full document text.

        Returns:
            List of text chunks, each around target_chunk_words.
        """
        if not text or not text.strip():
            return []
        text = text.strip()
        # Prefer paragraph-based for academic papers
        chunks = self.chunk_by_paragraphs(text)
        # Filter very small chunks by merging into previous
        merged = []
        for c in chunks:
            if self._word_count(c) >= self.min_chunk or not merged:
                merged.append(c)
            else:
                merged[-1] = merged[-1] + "\n\n" + c
        return merged
