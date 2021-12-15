from src.service_center import ServiceCenter, ServiceCenterEnum

SERVICE_CENTER_REGISTRY = {
    "SRC": ServiceCenter(ServiceCenterEnum.SRC),
    "LIN": ServiceCenter(ServiceCenterEnum.LIN),
}