import logging
from datetime import datetime
from enum import Enum, auto

import pandas as pd
import plotly.express as px
from scipy.stats import stats

from src.config.directories import directories
from src.constants import DATASET, HTML_FILENAME, PNG_FILENAME, APPLICATION_DATE

logger = logging.getLogger(__name__)

PERCENTILES = [0.05, 0.25, 0.5, 0.75, 0.93, 0.99]
DISTRIBUTION_COLUMNS = [f"{percentile * 100:.0f}%" for percentile in PERCENTILES]
CURRENT_YEAR = datetime.now().year


class ServiceCenterEnum(Enum):
    LIN = auto()
    SRC = auto()


class ServiceCenter:
    def __init__(
            self,
            service_center: ServiceCenterEnum = None,
            df_preprocessed: pd.DataFrame = None,
            df_processing_times_distribution: pd.DataFrame = None,
    ):
        self._service_center = service_center
        self._df_preprocessed = df_preprocessed
        self._df_processing_times_distribution = df_processing_times_distribution

    @property
    def service_center(self):
        return self._service_center

    @property
    def name(self):
        return self._service_center.name

    def _generate_preprocessed_forms_dataset(self) -> None:
        df = pd.read_csv(directories.data / DATASET)
        df_preprocessed = df.loc[df["service_center"] == self._service_center.name]

        for column_name in ["received_date", "priority_date", "notice_date"]:
            df_preprocessed.loc[:, column_name] = pd.to_datetime(
                df_preprocessed.loc[:, column_name], errors="coerce", utc=True
            )

        # Filter on NIW only and drop observations that don't have a service center or a received date
        df_preprocessed = df_preprocessed.loc[df_preprocessed["niw_flag"]].dropna(
            subset=["service_center", "received_date"], how="any"
        )

        # Filter out observations where notice date <= received date
        df_preprocessed = df_preprocessed.loc[
            df_preprocessed["notice_date"] > df_preprocessed["received_date"]
            ]

        # Add interesting features
        df_preprocessed["processing_time"] = (
                df_preprocessed["notice_date"] - df_preprocessed["received_date"]
        ).dt.days
        df_preprocessed["received_year"] = df_preprocessed["received_date"].dt.year
        df_preprocessed["notice_year"] = df_preprocessed["notice_date"].dt.year

        self._df_preprocessed = df_preprocessed.reset_index(drop=True)

    def _generate_processing_times_distribution(self) -> None:
        self._generate_preprocessed_forms_dataset()
        df_processing_times_distribution = self._df_preprocessed.groupby(
            ["notice_year"]
        )["processing_time"].describe(percentiles=PERCENTILES)
        df_processing_times_distribution = df_processing_times_distribution.loc[
            df_processing_times_distribution.index <= CURRENT_YEAR
            ]
        df_processing_times_distribution = df_processing_times_distribution.loc[2017:][
            DISTRIBUTION_COLUMNS
        ]
        self._df_processing_times_distribution = df_processing_times_distribution.apply(lambda x: round(x))

    @staticmethod
    def _get_days_since_application(application_date: str) -> int:
        days_since_application = datetime.today() - datetime.strptime(
            application_date, "%Y-%m-%d"
        )
        return days_since_application.days

    def plot_processing_times_distribution(self) -> None:
        self._generate_processing_times_distribution()
        fig = px.bar(
            self._df_processing_times_distribution.reset_index(),
            x="notice_year",
            y=DISTRIBUTION_COLUMNS,
            labels={"notice_year": "Year Approved", "value": "Days Elapsed"},
            title=f"{self._service_center.name} Processing Time - NIW w/ Chen Immigration",
            text="value",
        )

        fig.update_layout(barmode="group", legend_title="Distribution")
        fig.write_html(
            directories.html
            / HTML_FILENAME.format(service_center_name=self._service_center.name)
        )
        fig.write_image(
            directories.images
            / PNG_FILENAME.format(service_center_name=self._service_center.name)
        )
        fig.show()

    def get_percentile_of_days_elapsed(self) -> float:
        if self._df_preprocessed is None:
            self._generate_preprocessed_forms_dataset()
        # Filter on last 6 months only
        today = datetime.today()
        last6 = today - pd.DateOffset(months=6)
        self._df_preprocessed["notice_date"] = self._df_preprocessed[
            "notice_date"
        ].dt.tz_localize(
            None
        )  # get rid of timezone info
        df_6M = self._df_preprocessed.query(
            "(@today >= notice_date >= @last6)"
        ).reset_index(drop=True)

        processing_time_series = df_6M["processing_time"]
        percentile = round(
            stats.percentileofscore(
                processing_time_series,
                self._get_days_since_application(APPLICATION_DATE),
            ),
            2,
        )

        logger.info(
            f"Percentile of Days Elapsed Based on Last 6 Months of Chen Immigration I-140 NIW Data for {self._service_center.name}: {percentile}%"
        )
        return percentile
