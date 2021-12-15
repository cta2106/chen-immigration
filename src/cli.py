import argparse
import logging

from src.emailing.emailing import send_email
from src.scraper import Scraper
from src.service_center import ServiceCenter, ServiceCenterEnum

logger = logging.getLogger(__name__)

_SERVICE_CENTER_REGISTRY = {
    "SRC": ServiceCenter(ServiceCenterEnum.SRC),
    "LIN": ServiceCenter(ServiceCenterEnum.LIN),
}


def main():
    """ CLI entrypoint. """
    scraper = Scraper()
    scraper.run()

    args = _parse_cli()

    service_center = _SERVICE_CENTER_REGISTRY[args["service_center"]]
    service_center.plot_processing_times_distribution()
    # Determine percentile of days elapsed
    percentile_of_days_elapsed = service_center.get_percentile_of_days_elapsed()
    # Prepare email content
    html_content = f"""<strong>Percentile of Days Elapsed Based on Last 6 Months of Chen Immigration I-140 NIW Data for {service_center.name}: {percentile_of_days_elapsed}%</strong> """

    if args["send_email"]:
        send_email(html_content, service_center)


def _parse_cli():
    """ Parse the CLI argument, and return the args object. """
    parser = argparse.ArgumentParser(description="Chen Immigration EB2 NIW Processing")
    parser.add_argument("service_center", choices=_SERVICE_CENTER_REGISTRY.keys())
    parser.add_argument("-e", "--send_email", action="store_true", default=False)

    args = parser.parse_args()
    return args
