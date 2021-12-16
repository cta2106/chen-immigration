import datetime
from dataclasses import dataclass

from src.service_center import ServiceCenterEnum


@dataclass
class I140Form:
    filename: str
    niw_flag: bool
    received_date: datetime.datetime
    priority_date: datetime.datetime
    notice_date: datetime.datetime
    service_center: ServiceCenterEnum

    def as_dict(self):
        return {
            "filename": self.filename,
            "niw_flag": self.niw_flag,
            "received_date": self.received_date,
            "priority_date": self.priority_date,
            "notice_date": self.notice_date,
            "service_center": self.service_center.name
            if isinstance(self.service_center, ServiceCenterEnum)
            else None,
        }

    def __hash__(self):
        return hash(self.filename)
