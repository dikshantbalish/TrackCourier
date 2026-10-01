from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class ShipmentStatus(str, Enum):
    BOOKED = "Booked"
    PICKED_UP = "Picked Up"
    IN_TRANSIT = "In Transit"
    OUT_FOR_DELIVERY = "Out for Delivery"
    DELIVERED = "Delivered"
    EXCEPTION = "Exception"


_ALLOWED_STATUSES = ", ".join(f"'{status.value}'" for status in ShipmentStatus)
_STORED_STATUSES = f"{_ALLOWED_STATUSES}, 'At Hub'"


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        Index("ix_shipments_tracking_id", "tracking_id", unique=True),
        CheckConstraint("length(trim(tracking_id)) > 0", name="ck_shipments_tracking_id_not_empty"),
        CheckConstraint(
            f"status IN ({_STORED_STATUSES})",
            name="ck_shipments_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracking_id: Mapped[str] = mapped_column(String(100), nullable=False)
    current_status: Mapped[str] = mapped_column("status", String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    tracking_events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by=lambda: (TrackingEvent.event_time, TrackingEvent.id),
    )


class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_STORED_STATUSES})",
            name="ck_tracking_events_status",
        ),
        Index("ix_tracking_events_shipment_time", "shipment_id", "event_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    shipment: Mapped[Shipment] = relationship(back_populates="tracking_events")
