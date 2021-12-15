import base64
import os

from sendgrid import SendGridAPIClient, FileContent, FileName, FileType, Disposition
from sendgrid.helpers.mail import Mail, Attachment

from src.config.directories import directories
from src.constants import SENDER, RECIPIENTS, SUBJECT, PNG_FILENAME
from src.service_center import ServiceCenter


def send_email(html_content: str, service_center: ServiceCenter) -> None:
    message = Mail(
        from_email=SENDER,
        to_emails=RECIPIENTS,
        subject=SUBJECT,
        html_content=html_content,
    )

    with open(
        directories.images
        / PNG_FILENAME.format(service_center_name=service_center.name),
        "rb",
    ) as f:
        data = f.read()
        encoded_file = base64.b64encode(data).decode()

    attached_file = Attachment(
        FileContent(encoded_file),
        FileName(PNG_FILENAME.format(service_center_name=service_center.name)),
        FileType("image/png"),
        Disposition("attachment"),
    )
    message.attachment = attached_file

    sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
    sg.send(message)
