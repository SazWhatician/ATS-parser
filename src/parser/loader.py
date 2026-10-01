"""Document loader supporting PDF, DOCX, and TXT formats."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union, BinaryIO, Optional, Dict, Any
import io
import logging

logger = logging.getLogger(__name__)


@dataclass
class LoadedDocument:
    raw_text: str
    file_type: str
    page_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    filename: Optional[str] = None


class DocumentLoader:
    """Universal loader for PDF, DOCX, and TXT resume files."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    @classmethod
    def load_file(cls, file_path: Union[str, Path]) -> LoadedDocument:
        """Load document from a file path."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{suffix}'. Supported: {', '.join(cls.SUPPORTED_EXTENSIONS)}")

        if suffix == ".pdf":
            return cls._load_pdf(path)
        elif suffix == ".docx":
            return cls._load_docx(path)
        elif suffix == ".txt":
            return cls._load_txt(path)
        else:
            raise ValueError(f"Unsupported file format '{suffix}'")

    @classmethod
    def load_bytes(cls, data: bytes, filename: str) -> LoadedDocument:
        """Load document from in-memory byte buffer."""
        suffix = Path(filename).suffix.lower()
        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{suffix}'. Supported: {', '.join(cls.SUPPORTED_EXTENSIONS)}")

        stream = io.BytesIO(data)
        if suffix == ".pdf":
            return cls._load_pdf_stream(stream, filename)
        elif suffix == ".docx":
            return cls._load_docx_stream(stream, filename)
        elif suffix == ".txt":
            return cls._load_txt_bytes(data, filename)
        else:
            raise ValueError(f"Unsupported file format '{suffix}'")

    # --- PDF Processing ---

    @classmethod
    def _load_pdf(cls, path: Path) -> LoadedDocument:
        """Extract text from PDF using PyMuPDF (fitz) with pdfplumber fallback."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            pages_text = []
            for page in doc:
                text = page.get_text("text") or ""
                pages_text.append(text)
            page_count = len(doc)
            doc.close()
            full_text = "\n\n".join(pages_text)
            if full_text.strip():
                return LoadedDocument(
                    raw_text=full_text,
                    file_type="pdf",
                    page_count=page_count,
                    metadata={"engine": "pymupdf"},
                    filename=path.name
                )
        except Exception as e:
            logger.warning(f"PyMuPDF failed on {path.name}: {e}. Trying pdfplumber fallback.")

        # Fallback to pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
                return LoadedDocument(
                    raw_text="\n\n".join(pages_text),
                    file_type="pdf",
                    page_count=len(pdf.pages),
                    metadata={"engine": "pdfplumber"},
                    filename=path.name
                )
        except Exception as e:
            logger.error(f"pdfplumber also failed on {path.name}: {e}")
            raise RuntimeError(f"Failed to extract text from PDF '{path.name}': {e}")

    @classmethod
    def _load_pdf_stream(cls, stream: io.BytesIO, filename: str) -> LoadedDocument:
        """Extract text from in-memory PDF bytes."""
        try:
            import fitz
            doc = fitz.open(stream=stream.getvalue(), filetype="pdf")
            pages_text = [page.get_text("text") or "" for page in doc]
            page_count = len(doc)
            doc.close()
            return LoadedDocument(
                raw_text="\n\n".join(pages_text),
                file_type="pdf",
                page_count=page_count,
                metadata={"engine": "pymupdf"},
                filename=filename
            )
        except Exception as e:
            logger.warning(f"PyMuPDF stream extraction failed: {e}. Trying pdfplumber.")

        try:
            import pdfplumber
            stream.seek(0)
            with pdfplumber.open(stream) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
                return LoadedDocument(
                    raw_text="\n\n".join(pages_text),
                    file_type="pdf",
                    page_count=len(pdf.pages),
                    metadata={"engine": "pdfplumber"},
                    filename=filename
                )
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from PDF stream: {e}")

    # --- DOCX Processing ---

    @classmethod
    def _load_docx(cls, path: Path) -> LoadedDocument:
        """Extract text and table content from Microsoft Word document."""
        import docx
        doc = docx.Document(str(path))
        return cls._extract_docx_paragraphs_and_tables(doc, filename=path.name)

    @classmethod
    def _load_docx_stream(cls, stream: io.BytesIO, filename: str) -> LoadedDocument:
        """Extract text and tables from in-memory DOCX stream."""
        import docx
        doc = docx.Document(stream)
        return cls._extract_docx_paragraphs_and_tables(doc, filename=filename)

    @classmethod
    def _extract_docx_paragraphs_and_tables(cls, doc, filename: str) -> LoadedDocument:
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Also extract table text to avoid missing education or experience in tables
        table_rows = []
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    table_rows.append(" | ".join(row_cells))
                    
        full_text = "\n".join(paragraphs)
        if table_rows:
            full_text += "\n\n" + "\n".join(table_rows)

        return LoadedDocument(
            raw_text=full_text,
            file_type="docx",
            page_count=1,
            metadata={"paragraphs_count": len(paragraphs), "tables_count": len(doc.tables)},
            filename=filename
        )

    # --- TXT Processing ---

    @classmethod
    def _load_txt(cls, path: Path) -> LoadedDocument:
        """Extract text from plaintext file handling multiple encodings."""
        data = path.read_bytes()
        return cls._load_txt_bytes(data, filename=path.name)

    @classmethod
    def _load_txt_bytes(cls, data: bytes, filename: str) -> LoadedDocument:
        """Decode raw text bytes across UTF-8, Latin-1, and CP1252 encodings."""
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                text = data.decode(encoding)
                return LoadedDocument(
                    raw_text=text,
                    file_type="txt",
                    page_count=1,
                    metadata={"encoding": encoding},
                    filename=filename
                )
            except UnicodeDecodeError:
                continue

        # Fallback with replacement
        text = data.decode("utf-8", errors="replace")
        return LoadedDocument(
            raw_text=text,
            file_type="txt",
            page_count=1,
            metadata={"encoding": "utf-8-replace"},
            filename=filename
        )
