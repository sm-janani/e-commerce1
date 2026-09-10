"""
Lightweight Retrieval-Augmented Generation (RAG) module.

Loads all markdown files under data/knowledge_base/, splits them into
section-level chunks (by markdown headings), and retrieves the most
relevant chunks for a query using TF-IDF + cosine similarity.

This intentionally avoids requiring an external embeddings API or vector
database service, so the project runs end-to-end with just the Claude API
key. Swap `TfidfVectorizer` for a real embedding model + vector store
(e.g. Pinecone, Chroma, pgvector) for production use — see README.
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_DIR = Path(__file__).parent / "data" / "knowledge_base"


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


def _split_into_chunks(filepath: Path) -> List[Chunk]:
    """Split a markdown file into chunks at each '## ' heading."""
    content = filepath.read_text(encoding="utf-8")
    sections = re.split(r"\n(?=## )", content)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading_match = re.match(r"##\s+(.+)", section)
        heading = heading_match.group(1) if heading_match else filepath.stem
        chunks.append(Chunk(source=filepath.stem, heading=heading, text=section))
    return chunks


class KnowledgeBase:
    def __init__(self, kb_dir: Path = KB_DIR):
        self.chunks: List[Chunk] = []
        for md_file in sorted(kb_dir.glob("*.md")):
            self.chunks.extend(_split_into_chunks(md_file))

        if not self.chunks:
            raise RuntimeError(f"No knowledge base documents found in {kb_dir}")

        self._corpus = [c.text for c in self.chunks]
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(self._corpus)

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05) -> List[Chunk]:
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(zip(scores, self.chunks), key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in ranked[:top_k] if score >= min_score]

    def format_context(self, query: str, top_k: int = 3) -> str:
        results = self.search(query, top_k=top_k)
        if not results:
            return "No relevant policy or FAQ information was found for this query."
        formatted = []
        for chunk in results:
            formatted.append(f"[Source: {chunk.source} — {chunk.heading}]\n{chunk.text}")
        return "\n\n---\n\n".join(formatted)


# Singleton instance used by the agent
knowledge_base = KnowledgeBase()
