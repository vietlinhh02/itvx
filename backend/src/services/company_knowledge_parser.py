"""Parsing and chunking helpers for JD-scoped company knowledge documents."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from xml.etree import ElementTree
from zipfile import ZipFile


@dataclass(frozen=True)
class ParsedCompanyChunk:
    """One section-aware chunk extracted from a company document."""

    chunk_index: int
    section_title: str | None
    page_number: int | None
    content: str
    search_text: str


class CompanyKnowledgeParser:
    """Extract plain text and chunks from uploaded company knowledge files."""

    def parse(self, file_path: Path, mime_type: str) -> list[ParsedCompanyChunk]:
        """Parse one uploaded file into searchable chunks."""
        if mime_type == "application/pdf":
            text = self._parse_pdf(file_path)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = self._parse_docx(file_path)
        else:
            raise ValueError("Unsupported company document type")

        normalized_text = self._normalize_text(text)
        if not normalized_text:
            raise ValueError("Unable to extract text from company document")

        return self._chunk_text(normalized_text)

    def _parse_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF using pdftotext to avoid indexing raw PDF objects."""
        try:
            result = subprocess.run(
                ["pdftotext", str(file_path), "-"],
                capture_output=True,
                check=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("pdftotext is required to parse PDF company documents") from exc
        except subprocess.CalledProcessError as exc:
            error_message = (exc.stderr or "").strip() or "pdftotext failed"
            raise ValueError(f"Unable to extract text from PDF: {error_message}") from exc

        extracted_text = self._normalize_text(result.stdout)
        if not extracted_text:
            raise ValueError("Unable to extract text from PDF")
        return extracted_text

    def _parse_docx(self, file_path: Path) -> str:
        """Extract paragraph text from a DOCX archive."""
        with ZipFile(file_path) as archive:
            document_xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
            merged = "".join(texts).strip()
            if merged:
                paragraphs.append(merged)
        return "\n".join(paragraphs)

    def _normalize_text(self, text: str) -> str:
        """Collapse parser output into clean non-empty lines."""
        normalized = text.replace("\x00", " ")
        return "\n".join(line.strip() for line in normalized.splitlines() if line.strip())

    def _chunk_text(self, text: str) -> list[ParsedCompanyChunk]:
        """Split extracted text into section-aware chunks."""
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        if not paragraphs:
            return []

        sections: list[tuple[str | None, list[str]]] = []
        current_title: str | None = None
        current_lines: list[str] = []
        for paragraph in paragraphs:
            if self._looks_like_heading(paragraph):
                if current_lines:
                    sections.append((current_title, current_lines))
                current_title = paragraph
                current_lines = []
                continue
            current_lines.append(paragraph)
        if current_title is not None or current_lines:
            sections.append((current_title, current_lines))

        chunks: list[ParsedCompanyChunk] = []
        chunk_index = 0
        for section_title, lines in sections:
            if not lines and section_title:
                continue
            buffer: list[str] = []
            word_count = 0
            for line in lines or ([section_title] if section_title else []):
                line_words = len(line.split())
                if buffer and word_count + line_words > 140:
                    content = "\n".join(buffer).strip()
                    if content:
                        chunks.append(
                            ParsedCompanyChunk(
                                chunk_index=chunk_index,
                                section_title=section_title,
                                page_number=None,
                                content=content,
                                search_text=self._build_search_text(section_title, content),
                            )
                        )
                        chunk_index += 1
                    buffer = [line]
                    word_count = line_words
                    continue
                buffer.append(line)
                word_count += line_words
            content = "\n".join(buffer).strip()
            if content:
                chunks.append(
                    ParsedCompanyChunk(
                        chunk_index=chunk_index,
                        section_title=section_title,
                        page_number=None,
                        content=content,
                        search_text=self._build_search_text(section_title, content),
                    )
                )
                chunk_index += 1
        return chunks

    def _build_search_text(self, section_title: str | None, content: str) -> str:
        """Build the text field used by lexical retrieval."""
        if section_title:
            return f"{section_title}\n{content}"
        return content

    def _looks_like_heading(self, value: str) -> bool:
        """Heuristic to keep structured headings together during chunking."""
        stripped = value.strip()
        if not stripped:
            return False
        if len(stripped.split()) <= 8 and stripped.endswith(":"):
            return True
        return len(stripped) <= 80 and stripped.upper() == stripped
