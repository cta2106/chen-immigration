import logging
from typing import Set, List, Iterable, Optional
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ReadTimeout, ConnectionError, ChunkedEncodingError

from src.config.directories import directories
from src.constants import DATASET, URL_2019, URL_2020, URL_2021, URL_PRE_2019
from src.dataset_utils import read_i140_forms_from_csv
from src.file_utils import (
    get_files_in_dir,
    filename_from_url,
    filter_urls_based_on_filenames,
    get_chunked_form,
    find_pdfs_to_convert,
    png_to_pdf_filename,
    pdf_to_png_filename,
)
from src.form import I140Form
from src.image_to_form import image_to_form
from src.pdf_to_png import pdf_to_png

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self):
        self.page_urls = [URL_PRE_2019, URL_2019, URL_2020, URL_2021]
        self.i140_forms = set()
        self.form_urls = set()
        self.form_urls_to_scrape = set()

    def _populate_i140_forms_from_csv(self) -> None:
        self.i140_forms = read_i140_forms_from_csv()

    def _populate_form_urls(self) -> None:
        form_urls = set()
        for page_url in self.page_urls:
            r = requests.get(page_url)
            soup = BeautifulSoup(r.text, features="html.parser")
            table = soup.select_one("body > table")
            rows = table.select("tr > td:nth-child(2) > a")
            rows = rows[3:]  # drop header
            filenames = [row["href"] for row in rows]
            form_urls_on_page = [urljoin(page_url, name) for name in filenames]
            form_urls.update(form_urls_on_page)
        logger.info(
            f"Found a total of {len(form_urls)} urls on the Chen Immigration website."
        )
        self.form_urls = form_urls

    def _populate_form_urls_to_scrape(self) -> Set[str]:
        filenames_from_csv = {
            png_to_pdf_filename(form.filename) for form in self.i140_forms
        }
        filenames_from_website = {filename_from_url(url) for url in self.form_urls}

        filenames_to_scrape = filenames_from_website.difference(set(filenames_from_csv))
        logger.info(f"Filtering out urls already present in CSV...")

        form_urls_to_scrape = filter_urls_based_on_filenames(
            self.form_urls, filenames_to_scrape
        )
        logger.info(f"Found {len(form_urls_to_scrape)} new file(s) to scrape.")
        self.form_urls_to_scrape = form_urls_to_scrape

    def _get_pdfs_to_download(self) -> Set[str]:
        existing_pdfs = get_files_in_dir(directories.output, filetype=".pdf")
        pdf_filenames_to_scrape = {
            filename_from_url(f) for f in self.form_urls_to_scrape
        }
        pdf_filenames_to_download = pdf_filenames_to_scrape.difference(existing_pdfs)
        pdf_urls_to_download = filter_urls_based_on_filenames(
            self.form_urls_to_scrape, pdf_filenames_to_download
        )
        logger.info(
            f"Found {len(existing_pdfs)} existing PDFs in {directories.output}. Downloading {len(pdf_urls_to_download)} new PDFs."
        )
        return pdf_urls_to_download

    def _download_new_pdf_forms(self) -> None:
        pdf_urls_to_download = self._get_pdfs_to_download()
        for form_url in pdf_urls_to_download:
            local_filename = filename_from_url(form_url)
            try:
                get_chunked_form(form_url, local_filename)
            except (ConnectionError, ReadTimeout, ChunkedEncodingError) as e:
                logger.error(f"{e} for {form_url}")
                continue

    @staticmethod
    def _convert_new_pdf_forms_to_png() -> None:
        pdf_filenames_to_convert = find_pdfs_to_convert()
        for filename in pdf_filenames_to_convert:
            pdf_to_png(filename)
            logger.info(f"Converted {filename} to png.")

    def _generate_forms_to_scrape(self) -> Iterable:
        for form_url in self.form_urls_to_scrape:
            pdf_filename = filename_from_url(form_url)
            png_filename = pdf_to_png_filename(pdf_filename)
            form = image_to_form(png_filename)
            if form not in self.i140_forms:
                self.i140_forms.append(form)
                yield form.as_dict()
                logger.info(f"Added form {form.as_dict()} to forms.")

    def _write_forms_to_csv(self, *, chunk_size: int) -> None:
        chunk = list()
        existing_rows = len(self.form_urls) - len(self.form_urls_to_scrape)
        new_rows = 0

        for idx, form in enumerate(self._generate_forms_to_scrape()):
            chunk.append(form)
            if len(chunk) % chunk_size == 0 or idx == len(self.form_urls_to_scrape) - 1:
                existing_rows += chunk_size
                new_rows += chunk_size

                self._write_chunk(chunk, existing_rows)
                chunk = list()

    def _is_empty_csv(self):
        return len(self.form_urls) == len(self.form_urls_to_scrape)

    def _write_chunk(self, chunk: List[Optional[I140Form]], existing_rows: int) -> None:
        header = True if existing_rows == len(chunk) else False
        pd.DataFrame(chunk).to_csv(
            directories.data / DATASET, mode="a", header=header, index=False
        )
        logger.info(
            "Written {existing_rows} out of {form_urls} rows... {percent_complete:.3%} complete.".format(
                existing_rows=existing_rows,
                form_urls=len(self.form_urls),
                percent_complete=existing_rows / len(self.form_urls),
            )
        )

    def run(self):
        self._populate_i140_forms_from_csv()
        self._populate_form_urls()
        self._populate_form_urls_to_scrape()
        self._download_new_pdf_forms()
        self._convert_new_pdf_forms_to_png()
        self._write_forms_to_csv(chunk_size=1)
