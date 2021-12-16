import argparse
import logging

from src.constants.service_center_registry import SERVICE_CENTER_REGISTRY
from src.context import context
from src.distribution import process_distribution
from src.scraper import Scraper

logger = logging.getLogger(__name__)

_PIPELINES_REGISTRY = {"scrape": Scraper().run, "distribution": process_distribution}


def main() -> None:
    """ CLI entrypoint. """
    args = _parse_cli()

    for k, v in vars(args).items():
        setattr(context, k, v)

    pipeline = _PIPELINES_REGISTRY[context.pipeline]
    pipeline()


def _parse_cli() -> argparse.Namespace:
    """ Parse the CLI argument, and return the args object. """
    parser = argparse.ArgumentParser(description="Chen Immigration EB2 NIW Processing")
    parser.add_argument(
        "pipeline",
        choices=_PIPELINES_REGISTRY.keys(),
        help="Choose between scrape or distribution.",
    )
    parser.add_argument(
        "--service-center",
        choices=SERVICE_CENTER_REGISTRY.keys(),
        help="USCIS service center. Choose between SRC or LIN.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=25,
        help="Number of forms to save to disk at a time.",
    )
    parser.add_argument(
        "-e",
        "--send_email",
        action="store_true",
        default=False,
        help="Decide whether to send email with your distribution plot.",
    )

    args = parser.parse_args()
    _check_args(args, parser)
    return args


def _check_args(args, parser) -> None:
    """ Raise error if CLI args are not valid. """
    if args.pipeline == "distribution" and args.service_center is None:
        parser.error("pipeline 'distribution' requires --service-center.")
