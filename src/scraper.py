import logging
from typing import List, Iterable
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ReadTimeout, ConnectionError, ChunkedEncodingError

from src.config.directories import directories
from src.constants import DATASET, URL_2019, URL_2020, URL_2021, URL_PRE_2019
from src.dataset_utils import read_i140_forms_from_csv, get_number_of_rows_from_csv
from src.file_utils import (
    get_files_in_dir,
    filename_from_url,
    filter_urls_based_on_filenames,
    get_chunked_form,
    find_pdfs_to_convert,
    png_to_pdf_filename,
    pdf_to_png_filename,
)
from src.image_to_form import image_to_form
from src.pdf_to_png import pdf_to_png

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self):
        self.page_urls = [URL_PRE_2019, URL_2019, URL_2020, URL_2021]
        self.i140_forms = list()
        self.form_urls = list()
        self.form_urls_to_scrape = list()

    def _get_all_form_urls(self) -> List[str]:
        form_urls = list()
        for page_url in self.page_urls:
            r = requests.get(page_url)
            soup = BeautifulSoup(r.text, features="html.parser")
            table = soup.select_one("body > table")
            rows = table.select("tr > td:nth-child(2) > a")
            rows = rows[3:]  # drop header
            filenames = [row["href"] for row in rows]
            form_urls_on_page = [urljoin(page_url, name) for name in filenames]
            form_urls.extend(form_urls_on_page)
        logger.info(
            f"Found a total of {len(form_urls)} urls on the Chen Immigration website."
        )
        return form_urls

    def _filter_out_urls_in_csv(self) -> List[str]:
        filenames_from_csv = [
            png_to_pdf_filename(form.filename) for form in self.i140_forms
        ]
        filenames_from_website = [filename_from_url(url) for url in self.form_urls]

        filenames_to_scrape = set(filenames_from_website).difference(
            set(filenames_from_csv)
        )
        logger.info(
            f"Filtered out files in CSV... Number of remaining filenames to scrape: {len(filenames_to_scrape)}."
        )

        form_urls_to_scrape = filter_urls_based_on_filenames(
            set(self.form_urls), filenames_to_scrape
        )

        logger.info(
            f"Filtered out forms in CSV and found {len(form_urls_to_scrape)} new file(s) to scrape."
        )
        return form_urls_to_scrape

    def _filter_out_downloaded_pdfs(self) -> List[str]:
        existing_pdfs = get_files_in_dir(directories.output, filetype=".pdf")
        pdf_filenames_to_scrape = {
            filename_from_url(f) for f in self.form_urls_to_scrape
        }
        pdf_filenames_to_download = pdf_filenames_to_scrape.difference(existing_pdfs)
        pdf_urls_to_download = filter_urls_based_on_filenames(
            set(self.form_urls_to_scrape), pdf_filenames_to_download
        )
        logger.info(
            f"Found {len(existing_pdfs)} existing PDFs in {directories.output}. Downloading {len(pdf_urls_to_download)} new PDFs."
        )
        return pdf_urls_to_download

    def _download_new_pdf_forms(self) -> None:
        pdf_urls_to_download = self._filter_out_downloaded_pdfs()
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

    def _generate_forms(self) -> Iterable:
        for form_url in self.form_urls_to_scrape:
            pdf_filename = filename_from_url(form_url)
            png_filename = pdf_to_png_filename(pdf_filename)
            form = image_to_form(png_filename)
            if form not in self.i140_forms:
                self.i140_forms.append(form)
                yield form.as_dict()
                logger.info(f"Added form {form.as_dict()} to forms.")

    def _write_forms_to_csv(self, *, chunk_size) -> None:
        chunk = list()
        row_counter = get_number_of_rows_from_csv()
        for form in self._generate_forms():
            chunk.append(form)

            if len(chunk) == chunk_size:
                header = True if row_counter == 0 else False
                row_counter += chunk_size
                pd.DataFrame(chunk).to_csv(
                    directories.data / DATASET, mode="a", header=header, index=False
                )
                logger.info(
                    "Wrote {row_counter} out of {urls_to_scrape} rows... {percent_complete:.2%} complete.".format(
                        row_counter=row_counter,
                        urls_to_scrape=len(self.form_urls_to_scrape),
                        percent_complete=row_counter / len(self.form_urls_to_scrape),
                    )
                )
                chunk = list()

        # make sure to append the last chunk
        if len(chunk) > 0:
            pd.DataFrame(chunk).to_csv(
                directories.data / DATASET, mode="a", header=False, index=False
            )

    def run(self):
        self.i140_forms = read_i140_forms_from_csv()
        self.form_urls = self._get_all_form_urls()
        self.form_urls_to_scrape = self._filter_out_urls_in_csv()
        self._download_new_pdf_forms()
        self._convert_new_pdf_forms_to_png()
        self._write_forms_to_csv(chunk_size=1)
