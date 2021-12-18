import datetime
import logging
import time
from typing import Set, List, Iterable, Optional
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ReadTimeout, ConnectionError, ChunkedEncodingError

from src.config.directories import directories
from src.constants import DATASET, URL_2019, URL_2020, URL_2021, URL_PRE_2019
from src.context import context
from src.dataset_utils import read_i140_forms_from_csv
from src.file_utils import (
    get_files_in_dir,
    pdf_filename_from_url,
    filter_urls_based_on_filenames,
    png_to_pdf_filename,
    pdf_to_png_filename,
    get_chunked_form_content,
    filename_from_url,
)
from src.form import I140Form
from src.image_to_form import image_to_form
from src.pdf_to_png import download_pdf_content_as_png

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

    def _populate_form_urls_to_scrape(self) -> None:
        filenames_from_csv = {
            png_to_pdf_filename(form.filename) for form in self.i140_forms
        }
        filenames_from_website = {pdf_filename_from_url(url) for url in self.form_urls}

        filenames_to_scrape = filenames_from_website.difference(set(filenames_from_csv))
        logger.info(f"Filtering out urls already present in CSV...")

        form_urls_to_scrape = filter_urls_based_on_filenames(
            self.form_urls, filenames_to_scrape
        )
        logger.info(f"Found {len(form_urls_to_scrape)} new file(s) to scrape.")
        self.form_urls_to_scrape = form_urls_to_scrape

    def _get_forms_to_download(self) -> Set[str]:
        existing_pngs = get_files_in_dir(directories.output, filetype=".png")
        existing_pdfs = [png_to_pdf_filename(filename) for filename in existing_pngs]

        pdf_filenames_to_scrape = {
            pdf_filename_from_url(f) for f in self.form_urls_to_scrape
        }
        pdf_filenames_to_download = pdf_filenames_to_scrape.difference(existing_pdfs)
        pdf_urls_to_download = filter_urls_based_on_filenames(
            self.form_urls_to_scrape, pdf_filenames_to_download
        )
        logger.info(
            f"Found {len(existing_pdfs)} existing PNGs in {directories.output}. Downloading {len(pdf_urls_to_download)} new PNGs."
        )
        return pdf_urls_to_download

    def _generate_new_pdf_content(self) -> Iterable:
        pdf_urls_to_download = self._get_forms_to_download()
        for form_url in pdf_urls_to_download:
            try:
                content = get_chunked_form_content(form_url)
                yield content, form_url
            except (ConnectionError, ReadTimeout, ChunkedEncodingError) as e:
                logger.error(f"{e} for {form_url}")
                continue

    def _download_png_files(self) -> None:
        for content, form_url in self._generate_new_pdf_content():
            filename = filename_from_url(form_url)
            download_pdf_content_as_png(content, filename)
            logger.info(f"Downloaded {filename} as png.")

    def _generate_forms(self) -> Iterable:
        for form_url in self.form_urls_to_scrape:
            start = time.time()
            pdf_filename = pdf_filename_from_url(form_url)
            png_filename = pdf_to_png_filename(pdf_filename)
            form = image_to_form(png_filename)
            if form not in self.i140_forms:
                self.i140_forms.add(form)
                end = time.time()
                form_dict = form.as_dict() if form else None
                yield form_dict, end - start
                logger.info(f"Added form {form} to forms.")

    def _write_forms_to_csv(self, *, chunk_size: int) -> None:
        chunk = list()
        existing_rows = len(self.form_urls) - len(self.form_urls_to_scrape)
        new_rows = 0
        eta = list()

        for idx, (form, elapsed_time) in enumerate(self._generate_forms()):
            if form:
                chunk.append(form)
            if len(chunk) % chunk_size == 0 or idx == len(self.form_urls_to_scrape) - 1:
                existing_rows += chunk_size
                new_rows += chunk_size

                self._write_chunk(chunk, existing_rows)
                chunk = list()
                remaining_forms = len(self.form_urls) - existing_rows
                eta.append(datetime.timedelta(seconds=(remaining_forms * elapsed_time)))

                logger.info("Estimated time left: {}".format(np.mean(eta[-100:])))

    def _is_empty_csv(self):
        return len(self.form_urls) == len(self.form_urls_to_scrape)

    def _write_chunk(self, chunk: List[Optional[I140Form]], num_existing_rows: int) -> None:
        header = True if num_existing_rows == len(chunk) else False
        pd.DataFrame(chunk).to_csv(
            directories.data / DATASET, mode="a", header=header, index=False
        )
        logger.info(
            "Wrote {num_existing_rows} out of {form_urls} rows to disk... {percent_complete:.3%} complete.".format(
                num_existing_rows=num_existing_rows,
                form_urls=len(self.form_urls),
                percent_complete=num_existing_rows / len(self.form_urls),
            )
        )

    def run(self):
        self._populate_i140_forms_from_csv()
        self._populate_form_urls()
        self._populate_form_urls_to_scrape()
        self._download_png_files()
        self._write_forms_to_csv(chunk_size=context.chunk_size)
