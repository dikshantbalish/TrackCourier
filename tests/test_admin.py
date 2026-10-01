from datetime import UTC, datetime

from app.database.connection import SessionLocal
from app.models.shipment import TrackingEvent


def login_admin(client):
    return client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "a-test-password-with-12-chars"},
    )


def test_admin_can_create_update_track_and_delete_shipment(client, admin_account):
    assert login_admin(client).status_code == 200

    created = client.post(
        "/api/admin/shipments",
        json={
            "tracking_id": "  SB123456789  ",
            "status": "Booked",
            "location": "  Delhi  ",
            "description": "Shipment accepted at the counter.",
        },
    )
    assert created.status_code == 201
    shipment = created.json()
    assert shipment["tracking_id"] == "SB123456789"
    assert shipment["status"] == "Booked"
    assert shipment["location"] == "Delhi"
    assert "password_hash" not in shipment

    duplicate = client.post(
        "/api/admin/shipments",
        json={"tracking_id": "SB123456789", "status": "Booked"},
    )
    assert duplicate.status_code == 409

    updated = client.put(
        f"/api/admin/shipments/{shipment['id']}",
        json={
            "tracking_id": "SB123456789",
            "status": "In Transit",
            "location": "Mumbai",
            "description": "On the way.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "In Transit"
    assert updated.json()["location"] == "Mumbai"

    tracking = client.get("/api/tracking/SB123456789")
    assert tracking.status_code == 200
    assert [event["status"] for event in tracking.json()["history"]] == ["Booked", "In Transit"]

    deleted = client.delete(f"/api/admin/shipments/{shipment['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/tracking/SB123456789").status_code == 404
    with SessionLocal() as database:
        assert database.query(TrackingEvent).count() == 0


def test_admin_event_updates_shipment_status_atomically(client, admin_account):
    login_admin(client)
    created = client.post(
        "/api/admin/shipments",
        json={"tracking_id": "SB-EVENT-1", "status": "Booked"},
    )
    shipment_id = created.json()["id"]

    event = client.post(
        f"/api/admin/shipments/{shipment_id}/events",
        json={
            "status": "Picked Up",
            "description": "Parcel collected.",
            "location": "Delhi",
            "event_time": datetime(2026, 10, 1, 8, tzinfo=UTC).isoformat(),
        },
    )
    assert event.status_code == 201
    assert event.json()["status"] == "Picked Up"

    tracking = client.get("/api/tracking/SB-EVENT-1")
    assert tracking.status_code == 200
    assert tracking.json()["status"] == "Picked Up"
    event = next(event for event in tracking.json()["history"] if event["status"] == "Picked Up")
    assert event["location"] == "Delhi"


def test_invalid_status_is_rejected(client, admin_account):
    login_admin(client)
    response = client.post(
        "/api/admin/shipments",
        json={"tracking_id": "SB-INVALID", "status": "Teleporting"},
    )

    assert response.status_code == 422
