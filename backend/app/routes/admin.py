from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.admin import AdminUser
from app.models.shipment import Shipment
from app.routes.auth import require_admin
from app.schemas.shipment import (
    ShipmentAdminResponse,
    ShipmentCreate,
    ShipmentUpdate,
    TrackingEventCreate,
    TrackingEventResponse,
)
from app.services.shipment import (
    DuplicateTrackingIdError,
    ShipmentNotFoundError,
    add_tracking_event,
    create_shipment,
    delete_shipment,
    get_shipment,
    list_shipments,
    update_shipment,
)

router = APIRouter(prefix="/api/admin/shipments", tags=["admin shipments"])
ShipmentId = Annotated[int, Path(gt=0)]


def _raise_service_error(error: Exception) -> None:
    if isinstance(error, ShipmentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, DuplicateTrackingIdError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    raise error


@router.get("", response_model=list[ShipmentAdminResponse])
def get_shipments(
    _database: Session = Depends(get_db),
    _admin: AdminUser = Depends(require_admin),
) -> list[Shipment]:
    return list_shipments(_database)


@router.post("", response_model=ShipmentAdminResponse, status_code=status.HTTP_201_CREATED)
def post_shipment(
    data: ShipmentCreate,
    database: Session = Depends(get_db),
    _admin: AdminUser = Depends(require_admin),
) -> Shipment:
    try:
        return create_shipment(database, data)
    except (ShipmentNotFoundError, DuplicateTrackingIdError) as error:
        _raise_service_error(error)


@router.get("/{shipment_id}", response_model=ShipmentAdminResponse)
def get_shipment_detail(
    shipment_id: ShipmentId,
    database: Session = Depends(get_db),
    _admin: AdminUser = Depends(require_admin),
) -> Shipment:
    try:
        return get_shipment(database, shipment_id)
    except ShipmentNotFoundError as error:
        _raise_service_error(error)


@router.put("/{shipment_id}", response_model=ShipmentAdminResponse)
def put_shipment(
    shipment_id: ShipmentId,
    data: ShipmentUpdate,
    database: Session = Depends(get_db),
    _admin: AdminUser = Depends(require_admin),
) -> Shipment:
    try:
        return update_shipment(database, shipment_id, data)
    except (ShipmentNotFoundError, DuplicateTrackingIdError) as error:
        _raise_service_error(error)


@router.post(
    "/{shipment_id}/events",
    response_model=TrackingEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_tracking_event(
    shipment_id: ShipmentId,
    data: TrackingEventCreate,
    database: Session = Depends(get_db),
    _admin: AdminUser = Depends(require_admin),
) -> TrackingEventResponse:
    try:
        event = add_tracking_event(database, shipment_id, data)
        return TrackingEventResponse.model_validate(event)
    except ShipmentNotFoundError as error:
        _raise_service_error(error)


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shipment(
    shipment_id: ShipmentId,
    database: Session = Depends(get_db),
    _admin: AdminUser = Depends(require_admin),
) -> Response:
    try:
        delete_shipment(database, shipment_id)
    except ShipmentNotFoundError as error:
        _raise_service_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
