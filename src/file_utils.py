import logging
from os import listdir
from os.path import isfile
from pathlib import Path
from typing import Set, List

import requests

from src.config.directories import directories

logger = logging.getLogger(__name__)


def filename_from_url(url: str) -> str:
    return str(url).split("/")[-1]


def png_to_pdf_filename(png_filename: str) -> str:
    return str(png_filename).replace("0001-1.png", ".pdf")


def pdf_to_png_filename(pdf_filename: str) -> str:
    return str(pdf_filename).replace(".pdf", "0001-1.png")


def get_files_in_dir(directory: Path, *, filetype: str) -> Set[str]:
    return {f for f in listdir(directory) if (isfile(directory / f) and filetype in f)}


def filter_urls_based_on_filenames(
    url_set: Set[str], filename_set: Set[str]
) -> Set[str]:
    return {s for s in url_set if any(sub == s.split("/")[-1] for sub in filename_set)}


def get_chunked_form(form_url: str, local_filename: str) -> None:
    with requests.get(form_url, stream=True) as r:
        r.raise_for_status()
        with open(directories.output / local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    logger.info(f"Downloaded {local_filename}")


def find_pdfs_to_convert() -> List[str]:
    pdf_filenames = get_files_in_dir(directories.output, filetype=".pdf")
    png_filenames = get_files_in_dir(directories.output, filetype=".png")
    logger.info(f"Found {len(png_filenames)} PNG files.")
    pdfs_to_convert = list(
        pdf_filenames.difference({png_to_pdf_filename(f) for f in png_filenames})
    )
    logger.info(f"Converting remaining {len(pdfs_to_convert)} PDF files to PNG.")
    return pdfs_to_convert
