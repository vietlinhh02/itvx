"""Company knowledge parser regression tests."""

from subprocess import CompletedProcess
from typing import Any

import pytest

from src.services import company_knowledge_parser
from src.services.company_knowledge_parser import CompanyKnowledgeParser


def test_parse_pdf_uses_pdftotext_output(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """PDF parsing should use extracted text instead of raw PDF object bytes."""
    pdf_path = tmp_path / "company.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n")

    def fake_run(*args: Any, **kwargs: Any) -> CompletedProcess[str]:
        assert args == (["pdftotext", str(pdf_path), "-"],)
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is True
        assert kwargs["text"] is True
        return CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="Benefits:\n15 days annual leave\nHybrid work policy\n",
            stderr="",
        )

    monkeypatch.setattr(company_knowledge_parser.subprocess, "run", fake_run)

    chunks = CompanyKnowledgeParser().parse(pdf_path, "application/pdf")

    assert len(chunks) == 1
    assert chunks[0].section_title == "Benefits:"
    assert "15 days annual leave" in chunks[0].content
    assert "1 0 obj" not in chunks[0].content


def test_parse_pdf_raises_when_no_text_can_be_extracted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """PDF parsing should fail fast when extraction yields no usable text."""
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    def fake_run(*args: Any, **kwargs: Any) -> CompletedProcess[str]:
        _ = (args, kwargs)
        return CompletedProcess(
            args=["pdftotext", str(pdf_path), "-"],
            returncode=0,
            stdout=" \n\t",
            stderr="",
        )

    monkeypatch.setattr(company_knowledge_parser.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="Unable to extract text from PDF"):
        CompanyKnowledgeParser().parse(pdf_path, "application/pdf")
