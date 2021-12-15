import logging

from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError

from src.config.directories import directories

logger = logging.getLogger(__name__)


def pdf_to_png(local_filename: str) -> None:
    try:
        convert_from_path(
            directories.output / local_filename,
            output_folder="output",
            fmt="png",
            output_file=local_filename.split(".pdf")[0],
        )
    except PDFPageCountError as e:
        logger.error(
            f"PDFPageCountError: {e} encountered while converting {local_filename}."
        )
