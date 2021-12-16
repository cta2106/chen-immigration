from src.constants import EMAIL_HTML_CONTENT
from src.constants.registry import SERVICE_CENTER_REGISTRY
from src.context import context
from src.emailing.emailing import send_email


def process_distribution() -> None:
    service_center = SERVICE_CENTER_REGISTRY[context.service_center]

    service_center.plot_processing_times_distribution()
    percentile_of_days_elapsed = service_center.get_percentile_of_days_elapsed()
    html_content = EMAIL_HTML_CONTENT.format(
        service_center_name=service_center.name,
        percentile_of_days_elapsed=percentile_of_days_elapsed,
    )

    if context.send_email:
        send_email(html_content, service_center)
