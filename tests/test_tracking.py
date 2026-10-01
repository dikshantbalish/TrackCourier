from datetime import UTC, datetime

from app.database.connection import SessionLocal
from app.models.shipment import Shipment, ShipmentStatus, TrackingEvent


def test_tracking_returns_customer_fields_and_chronological_history(client):
    with SessionLocal() as database:
        shipment = Shipment(
            tracking_id="SB123456789",
            current_status=ShipmentStatus.IN_TRANSIT.value,
            description="Parcel is moving between facilities.",
        )
        shipment.tracking_events.extend(
            [
                TrackingEvent(
                    status=ShipmentStatus.IN_TRANSIT.value,
                    description="Parcel accepted for transit.",
                    event_time=datetime(2026, 10, 1, 8, tzinfo=UTC),
                ),
                TrackingEvent(
                    status=ShipmentStatus.BOOKED.value,
                    description="Shipment booked.",
                    event_time=datetime(2026, 9, 30, 10, tzinfo=UTC),
                ),
            ]
        )
        database.add(shipment)
        database.commit()

    response = client.get("/api/tracking/%20SB123456789%20")

    assert response.status_code == 200
    data = response.json()
    assert data["tracking_id"] == "SB123456789"
    assert data["status"] == "In Transit"
    assert [event["status"] for event in data["history"]] == ["Booked", "In Transit"]
    assert data["history"][0]["timestamp"].endswith(("Z", "+00:00"))
    assert "id" not in data
    assert "password_hash" not in data


def test_unknown_tracking_id_returns_safe_not_found(client):
    response = client.get("/api/tracking/NOT-A-REAL-ID")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tracking ID not found"}


def test_whitespace_tracking_id_is_rejected(client):
    response = client.get("/api/tracking/%20%20")

    assert response.status_code == 422
    assert "Tracking ID must not be empty" in str(response.json())


def test_legacy_at_hub_status_is_normalized_for_customers(client):
    with SessionLocal() as database:
        database.add(Shipment(tracking_id="SB-LEGACY-1", current_status="At Hub"))
        database.commit()

    response = client.get("/api/tracking/SB-LEGACY-1")

    assert response.status_code == 200
    assert response.json()["status"] == "In Transit"
    assert response.json()["history"] == []
