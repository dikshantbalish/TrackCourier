from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.shipment import Shipment, TrackingEvent
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate, TrackingEventCreate


class ShipmentNotFoundError(Exception):
    pass


class DuplicateTrackingIdError(Exception):
    pass


def _commit(database: Session) -> None:
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise DuplicateTrackingIdError("Tracking ID already exists") from error


def get_shipment(database: Session, shipment_id: int) -> Shipment:
    shipment = database.scalar(
        select(Shipment)
        .options(selectinload(Shipment.tracking_events))
        .where(Shipment.id == shipment_id)
    )
    if shipment is None:
        raise ShipmentNotFoundError("Shipment not found")
    return shipment


def list_shipments(database: Session) -> list[Shipment]:
    return list(
        database.scalars(select(Shipment).order_by(Shipment.updated_at.desc(), Shipment.id.desc()))
    )


def create_shipment(database: Session, data: ShipmentCreate) -> Shipment:
    shipment = Shipment(
        tracking_id=data.tracking_id,
        current_status=data.status.value,
        location=data.location.strip() if data.location and data.location.strip() else None,
        description=data.description,
    )
    shipment.tracking_events.append(
        TrackingEvent(status=data.status.value, description=data.description)
    )
    database.add(shipment)
    _commit(database)
    return shipment


def update_shipment(database: Session, shipment_id: int, data: ShipmentUpdate) -> Shipment:
    shipment = get_shipment(database, shipment_id)
    previous_status = shipment.current_status
    changes = data.model_fields_set

    if data.tracking_id is not None:
        shipment.tracking_id = data.tracking_id
    if data.status is not None:
        shipment.current_status = data.status.value
    if "location" in changes:
        shipment.location = data.location.strip() if data.location and data.location.strip() else None
    if "description" in changes:
        shipment.description = data.description

    if data.status is not None and data.status.value != previous_status:
        shipment.tracking_events.append(
            TrackingEvent(status=data.status.value, description=data.description)
        )
    if changes:
        shipment.updated_at = datetime.now(UTC)

    _commit(database)
    return shipment


def add_tracking_event(
    database: Session, shipment_id: int, data: TrackingEventCreate
) -> TrackingEvent:
    shipment = get_shipment(database, shipment_id)
    event = TrackingEvent(
        status=data.status.value,
        description=data.description,
        location=data.location,
        event_time=data.event_time,
    )
    shipment.tracking_events.append(event)
    shipment.current_status = data.status.value
    shipment.description = data.description
    shipment.updated_at = datetime.now(UTC)
    _commit(database)
    return event


def delete_shipment(database: Session, shipment_id: int) -> None:
    shipment = get_shipment(database, shipment_id)
    database.delete(shipment)
    _commit(database)
