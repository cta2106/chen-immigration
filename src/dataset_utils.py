import logging
from typing import Optional, Set

import pandas as pd

from src.config.directories import directories
from src.constants import DATASET
from src.form import I140Form
from src.service_center import ServiceCenterEnum

logger = logging.getLogger(__name__)


def process_forms_dataframe(df: pd.DataFrame) -> Set[I140Form]:
    i140_data = set()
    for _, row in df.iterrows():
        row = process_service_center(row)
        i140_data.add(I140Form(**row))
    logger.info(f"Found {len(i140_data)} forms in the CSV file.")
    return i140_data


def process_service_center(row: pd.Series) -> pd.Series:
    try:
        enum_val = ServiceCenterEnum[row["service_center"]]
    except KeyError:
        enum_val = None
    row["service_center"] = enum_val
    return row


def read_i140_forms_from_csv() -> Set[Optional[I140Form]]:
    try:
        df = pd.read_csv(directories.data / DATASET)
        i140_data = process_forms_dataframe(df)
        return i140_data
    except FileNotFoundError:
        logger.info(f"CSV file not found... creating empty file")
        with open(directories.data / DATASET, mode="a"):
            pass
        return set()
    except pd.errors.EmptyDataError:
        logger.info(f"CSV file is empty.")
        return set()
