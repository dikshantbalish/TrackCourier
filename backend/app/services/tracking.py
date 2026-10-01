from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.shipment import Shipment
from app.schemas.shipment import PublicTrackingResponse, TrackingEventResponse
from app.services.shipment import ShipmentNotFoundError


def get_public_tracking(database: Session, tracking_id: str) -> PublicTrackingResponse:
    normalized_id = tracking_id.strip()
    if not normalized_id:
        raise ValueError("Tracking ID must not be empty")

    shipment = database.scalar(
        select(Shipment)
        .options(selectinload(Shipment.tracking_events))
        .where(Shipment.tracking_id == normalized_id)
    )
    if shipment is None:
        raise ShipmentNotFoundError("Tracking ID not found")

    return PublicTrackingResponse(
        tracking_id=shipment.tracking_id,
        status=shipment.current_status,
        description=shipment.description,
        last_updated=shipment.updated_at,
        history=[TrackingEventResponse.model_validate(event) for event in shipment.tracking_events],
    )
