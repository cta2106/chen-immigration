import datetime
import logging
from typing import Tuple, Union

from dateparser.search import search_dates
from dateparser_data.settings import default_parsers

parsers = [parser for parser in default_parsers if parser != "relative-time"]

logger = logging.getLogger(__name__)


def get_dates(
    text: str,
) -> Union[
    Tuple[datetime.datetime, datetime.datetime, datetime.datetime],
    Tuple[None, None, None],
]:
    try:
        result = search_dates(
            text,
            settings={
                "STRICT_PARSING": False,
                "PARSERS": parsers,
                "REQUIRE_PARTS": ["month", "year"],
            },
            languages=["en"],
        )
    except TypeError as e:
        logger.error(f"{e} encountered while trying to parse {text}")
        result = None

    if result:
        _, dates = zip(*result[:3])

        if len(dates) == 3:
            return tuple(dates)
        else:
            return None, None, None
    else:
        return None, None, None
