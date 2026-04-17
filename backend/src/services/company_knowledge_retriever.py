"""Lexical retrieval for JD-scoped company knowledge documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.jd import JDCompanyChunk, JDCompanyDocument


@dataclass(frozen=True)
class RetrievedCompanyChunk:
    """One retrieved chunk plus citation metadata."""

    chunk_id: str
    document_id: str
    file_name: str
    section_title: str | None
    page_number: int | None
    excerpt: str
    score: int


class CompanyKnowledgeRetriever:
    """Query JD-scoped company knowledge using lexical scoring."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def retrieve(self, jd_id: str, query: str, limit: int = 5) -> list[RetrievedCompanyChunk]:
        """Return the top matching chunks for one JD."""
        terms = self._normalize_terms(query)
        if not terms:
            return []

        statement = (
            select(JDCompanyChunk, JDCompanyDocument)
            .join(JDCompanyDocument, JDCompanyDocument.id == JDCompanyChunk.jd_company_document_id)
            .where(
                JDCompanyChunk.jd_document_id == jd_id,
                JDCompanyDocument.status == "ready",
            )
        )
        rows = (await self._db_session.execute(statement)).all()

        matches: list[RetrievedCompanyChunk] = []
        for chunk, document in rows:
            score = self._score_chunk(query, terms, chunk.search_text, chunk.section_title)
            if score <= 0:
                continue
            matches.append(
                RetrievedCompanyChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    file_name=document.file_name,
                    section_title=chunk.section_title,
                    page_number=chunk.page_number,
                    excerpt=chunk.content,
                    score=score,
                )
            )

        matches.sort(key=lambda item: (-item.score, item.file_name, item.chunk_id))
        return matches[:limit]

    def _normalize_terms(self, query: str) -> list[str]:
        """Normalize a user query into lexical search terms."""
        return [term for term in re.findall(r"[\wÀ-ỹ-]{2,}", query.casefold()) if term]

    def _score_chunk(
        self,
        query: str,
        terms: list[str],
        search_text: str,
        section_title: str | None,
    ) -> int:
        """Score one chunk using exact phrase and token overlap."""
        haystack = search_text.casefold()
        score = 0
        if query.casefold() in haystack:
            score += 8
        for term in terms:
            if term in haystack:
                score += 2
            if section_title and term in section_title.casefold():
                score += 3
        return score
