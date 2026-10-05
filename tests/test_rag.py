from pathlib import Path
from app.citations import format_citation
from app.chunking import chunk_text
from app.excel_serializer import serialize_rows
from app.generator import MockLLMClient, REFUSAL
from app.models import DocumentChunk, RetrievedChunk


def test_chunking_preserves_metadata():
    chunks = chunk_text("alpha\n\nbeta", {"source": "x.pdf", "page": 2}, "recursive")
    assert chunks and chunks[0].metadata["page"] == 2


def test_excel_serializers():
    rows = [{"Region": "West", "Q1": 3500, "Q3": 4200}]
    assert "Region: West" in serialize_rows(rows, "row_text")[0]
    assert "| Region |" in serialize_rows(rows, "markdown_table")[0]
    assert "Q3: 4200" in serialize_rows(rows, "column_wise")[0]


def test_citation_metadata():
    assert format_citation({"source": "sales.xlsx", "sheet": "Sales", "row": 5}) == "[sales.xlsx, Sales sheet, row 5]"


def test_grounded_refusal():
    assert MockLLMClient().generate("unknown", "", []) == REFUSAL


def test_image_only_chart_is_not_in_pdf_text():
    chunk = DocumentChunk("The chart is shown below.", {"source": "spec.pdf", "page": 1})
    result = MockLLMClient().generate("What is West 4200?", "", [RetrievedChunk(chunk, 0.1, 0.9)])
    assert "4200" not in result
