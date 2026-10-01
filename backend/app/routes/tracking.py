from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.shipment import PublicTrackingResponse
from app.services.shipment import ShipmentNotFoundError
from app.services.tracking import get_public_tracking

router = APIRouter(prefix="/api/tracking", tags=["public tracking"])


@router.get("/{tracking_id}", response_model=PublicTrackingResponse)
def track_shipment(
    tracking_id: Annotated[str, Path(min_length=1, max_length=100)],
    database: Session = Depends(get_db),
) -> PublicTrackingResponse:
    try:
        return get_public_tracking(database, tracking_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except ShipmentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
