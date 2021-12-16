import logging
from os import listdir
from os.path import isfile
from pathlib import Path
from typing import Set

import requests

logger = logging.getLogger(__name__)


def filename_from_url(url: str) -> str:
    return pdf_filename_from_url(url).split(".pdf")[0]


def pdf_filename_from_url(url: str) -> str:
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


def get_chunked_form_content(form_url: str) -> bytearray:
    with requests.get(form_url, stream=True) as r:
        r.raise_for_status()
        content = bytearray()
        for chunk in r.iter_content(chunk_size=8192):
            content.extend(chunk)
    return content
