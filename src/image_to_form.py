import logging

import pytesseract

from src.config.directories import directories
from src.dates import get_dates
from src.form import I140Form
from src.service_center import ServiceCenterEnum

CUSTOM_CONFIG = r"--oem 3 --psm 6"

logger = logging.getLogger(__name__)


def image_to_form(local_filename: str) -> I140Form:
    try:
        text = pytesseract.image_to_string(
            str(directories.output / local_filename), config=CUSTOM_CONFIG
        )

        received_date, priority_date, notice_date = get_dates(text)

        form = I140Form(
            filename=local_filename,
            niw_flag="Indiv w/Adv Deg" in text,
            received_date=received_date,
            priority_date=priority_date,
            notice_date=notice_date,
            service_center=ServiceCenterEnum.SRC
            if "SRC" in text
            else ServiceCenterEnum.LIN
            if "LIN" in text
            else None,
        )
        return form
    except pytesseract.pytesseract.TesseractError as e:
        logger.error(f"{e} for file {local_filename}")
