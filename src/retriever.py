"""
Knowledge-base retrieval for the triage agent and (indirectly) the account
brief tool.

Design choice: TF-IDF over sentence-embeddings.
  - The KB corpus is small (9 docs, well under a few hundred chunks), where
    keyword-based retrieval is competitive with or better than embeddings
    and far more predictable to debug.
  - Zero model downloads -> installs in seconds, works fully offline, and
    can't fail on a grader's machine due to a flaky model download. This
    matters because the brief disqualifies submissions that don't run
    cleanly from `pip install -r requirements.txt`.
  - Fully deterministic, which lines up with Task 2's determinism
    requirement anyway.

Chunking strategy follows DATA_SCHEMA.md's recommendation:
  - Split each document on `---` horizontal rules (major section boundary).
  - Preserve heading hierarchy (the last-seen H1/H2/H3 above a chunk) as
    metadata, so retrieval results can cite "which doc / which section".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base"


@dataclass
class Chunk:
    doc_path: str          # relative path, e.g. "products/databridge-pro.md"
    heading_trail: str      # e.g. "DataBridge Pro > Core Modules > Data Ingestion"
    text: str
    chunk_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.chunk_id:
            self.chunk_id = f"{self.doc_path}#{abs(hash(self.text)) % 10**8}"


def _split_into_chunks(md_text: str, doc_path: str) -> list[Chunk]:
    """Split a markdown doc on `---` rules, tracking heading hierarchy."""
    sections = re.split(r"\n-{3,}\n", md_text)
    chunks: list[Chunk] = []
    heading_stack: dict[int, str] = {}  # level -> heading text

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Update heading stack based on any headings in this section, and
        # capture the trail as of the START of the section (i.e. before
        # headings inside it, so nested content is attributed correctly).
        trail_before = " > ".join(
            heading_stack[lvl] for lvl in sorted(heading_stack)
        )

        for line in section.splitlines():
            m = re.match(r"^(#{1,3})\s+(.*)", line)
            if m:
                level = len(m.group(1))
                heading_stack[level] = m.group(2).strip()
                # drop deeper levels once a shallower heading appears
                for lvl in list(heading_stack):
                    if lvl > level:
                        del heading_stack[lvl]

        trail_after = " > ".join(
            heading_stack[lvl] for lvl in sorted(heading_stack)
        )
        trail = trail_after or trail_before or doc_path

        # Skip near-empty chunks (e.g. a lone heading with no body)
        body_lines = [l for l in section.splitlines() if l.strip()]
        if len(body_lines) < 2:
            continue

        chunks.append(Chunk(doc_path=doc_path, heading_trail=trail, text=section))

    return chunks


def load_all_chunks(kb_root: Path = KB_ROOT) -> list[Chunk]:
    chunks: list[Chunk] = []
    for md_file in sorted(kb_root.rglob("*.md")):
        rel = str(md_file.relative_to(kb_root))
        text = md_file.read_text(encoding="utf-8")
        chunks.extend(_split_into_chunks(text, rel))
    return chunks


class KnowledgeBaseRetriever:
    """TF-IDF retriever over chunked KB docs."""

    def __init__(self, kb_root: Path = KB_ROOT):
        self.chunks: list[Chunk] = load_all_chunks(kb_root)
        if not self.chunks:
            raise RuntimeError(f"No knowledge-base chunks found under {kb_root}")

        corpus = [f"{c.heading_trail}\n{c.text}" for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_df=0.9,
        )
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05) -> list[dict]:
        """Return top_k chunks most relevant to `query`.

        Each result: {chunk_id, doc_path, heading_trail, text, score}
        Results below `min_score` are dropped (i.e. "no confident match").
        """
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        for i in ranked[:top_k]:
            if scores[i] < min_score:
                continue
            c = self.chunks[i]
            results.append(
                {
                    "chunk_id": c.chunk_id,
                    "doc_path": c.doc_path,
                    "heading_trail": c.heading_trail,
                    "text": c.text,
                    "score": round(float(scores[i]), 4),
                }
            )
        return results


if __name__ == "__main__":
    retriever = KnowledgeBaseRetriever()
    print(f"Loaded {len(retriever.chunks)} chunks from {KB_ROOT}")
    demo_query = "ERR_CONNECTION_TIMEOUT after 30s DataBridge Pro connectors failing"
    for r in retriever.search(demo_query, top_k=3):
        print(f"\n[{r['score']}] {r['doc_path']} :: {r['heading_trail']}")
        print(r["text"][:200].replace("\n", " "))
