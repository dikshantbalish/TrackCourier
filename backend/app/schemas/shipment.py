from datetime import UTC, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.models.shipment import ShipmentStatus


class ShipmentCreate(BaseModel):
    tracking_id: str = Field(min_length=1, max_length=100)
    status: ShipmentStatus
    location: str | None = Field(default=None, max_length=120)
    description: str | None = Field(
        default=None,
        max_length=2000,
        validation_alias=AliasChoices("description", "message"),
    )

    @field_validator("tracking_id")
    @classmethod
    def normalize_tracking_id(cls, value: str) -> str:
        tracking_id = value.strip()
        if not tracking_id:
            raise ValueError("Tracking ID must not be empty")
        return tracking_id


class ShipmentUpdate(BaseModel):
    tracking_id: str | None = Field(default=None, min_length=1, max_length=100)
    status: ShipmentStatus | None = None
    location: str | None = Field(default=None, max_length=120)
    description: str | None = Field(
        default=None,
        max_length=2000,
        validation_alias=AliasChoices("description", "message"),
    )

    @field_validator("tracking_id")
    @classmethod
    def normalize_tracking_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        tracking_id = value.strip()
        if not tracking_id:
            raise ValueError("Tracking ID must not be empty")
        return tracking_id


class TrackingEventCreate(BaseModel):
    status: ShipmentStatus
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    event_time: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("event_time")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class TrackingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: ShipmentStatus
    description: str | None
    location: str | None
    timestamp: datetime = Field(validation_alias="event_time")

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def normalize_legacy_status(value: ShipmentStatus | str) -> ShipmentStatus | str:
    return ShipmentStatus.IN_TRANSIT if value == "At Hub" else value


class ShipmentAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_id: str
    status: ShipmentStatus = Field(validation_alias="current_status")
    description: str | None
    location: str | None = None
    created_at: datetime
    updated_at: datetime = Field(validation_alias="updated_at")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: ShipmentStatus | str) -> ShipmentStatus | str:
        return normalize_legacy_status(value)

    @field_validator("created_at", "updated_at")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class PublicTrackingResponse(BaseModel):
    tracking_id: str
    status: ShipmentStatus
    description: str | None
    last_updated: datetime
    history: list[TrackingEventResponse]

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: ShipmentStatus | str) -> ShipmentStatus | str:
        return normalize_legacy_status(value)

    @field_validator("last_updated")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value
