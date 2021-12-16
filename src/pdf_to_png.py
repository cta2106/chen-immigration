import logging

from pdf2image import convert_from_bytes
from pdf2image.exceptions import PDFPageCountError

from src.config.directories import directories

logger = logging.getLogger(__name__)


def download_pdf_content_as_png(pdf_bytes: bytes, filename: str) -> None:
    try:
        convert_from_bytes(
            pdf_bytes, output_folder=directories.output, fmt="png", output_file=filename
        )
    except PDFPageCountError as e:
        logger.error(f"PDFPageCountError: {e} encountered while converting {filename}.")
