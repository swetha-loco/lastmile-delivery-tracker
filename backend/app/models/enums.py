from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    DELIVERY_AGENT = "DELIVERY_AGENT"
    ADMIN = "ADMIN"


class OrderType(StrEnum):
    B2B = "B2B"
    B2C = "B2C"


class PaymentType(StrEnum):
    PREPAID = "PREPAID"
    COD = "COD"


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RESCHEDULED = "RESCHEDULED"


class AgentAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class DeliveryAttemptStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class NotificationChannel(StrEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    RETRY = "RETRY"
    SENT = "SENT"
    FAILED = "FAILED"
