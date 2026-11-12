from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.audit import record_admin_action


client = TestClient(app)


def test_audit_event_records_only_minimal_metadata():
    actor_id = uuid4()
    actor = SimpleNamespace(id=actor_id, role="admin")
    resource_id = uuid4()

    class FakeSession:
        item = None

        def add(self, item):
            self.item = item

    db = FakeSession()
    record_admin_action(
        db, actor, "exam.approve", "exam", resource_id,
        "Sınav yayımlandı.",
    )

    assert db.item.actor_id == actor_id
    assert db.item.action == "exam.approve"
    assert db.item.resource_type == "exam"
    assert db.item.resource_id == str(resource_id)
    assert db.item.summary == "Sınav yayımlandı."
    assert not hasattr(db.item, "password")
    assert not hasattr(db.item, "token")


def test_non_admin_does_not_create_audit_event():
    actor = SimpleNamespace(id=uuid4(), role="student")

    class FakeSession:
        item = None

        def add(self, item):
            self.item = item

    db = FakeSession()
    record_admin_action(db, actor, "exam.approve", "exam")
    assert db.item is None


def test_admin_audit_endpoint_requires_authentication():
    response = client.get("/api/admin/audit-logs")
    assert response.status_code == 401


def test_admin_audit_endpoint_is_registered():
    assert "/api/admin/audit-logs" in app.openapi()["paths"]



def test_parent_cannot_read_admin_audit_logs():
    email = f"audit-parent-{uuid4()}@example.com"
    registered = client.post("/api/auth/register", json={
        "email": email, "password": "Long-Test-Password-2026", "full_name": "Denetim Velisi"
    })
    assert registered.status_code == 201
    token = client.post("/api/auth/login", json={
        "email": email, "password": "Long-Test-Password-2026"
    }).json()["access_token"]
    response = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
