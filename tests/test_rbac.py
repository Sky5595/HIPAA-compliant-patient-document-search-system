"""RBAC tests — mocks config path so tests work anywhere."""
import pytest
from unittest.mock import patch

MOCK_CFG = {
    "roles": {
        "physician": {
            "permissions": ["read:all", "write:wiki", "ingest:all", "query:all", "lint:run"],
            "patient_scope": "assigned_only"
        },
        "admin": {
            "permissions": ["read:audit_log", "manage:users"],
            "patient_scope": "none"
        },
        "nurse": {
            "permissions": ["read:all", "query:all"],
            "patient_scope": "assigned_only"
        }
    },
    "users": [
        {"username": "dr_smith",   "role": "physician", "assigned_patients": ["PT-0001"], "active": True},
        {"username": "hia_admin",  "role": "admin",     "assigned_patients": [],          "active": True},
        {"username": "nurse_jones","role": "nurse",     "assigned_patients": ["PT-0001"], "active": True},
    ]
}

import src.rbac as rbac

@pytest.fixture(autouse=True)
def mock_config():
    with patch.object(rbac, "_load_config", return_value=MOCK_CFG):
        yield

def test_physician_can_ingest_assigned():
    assert rbac.has_permission("dr_smith", "ingest:all", "PT-0001") is True

def test_physician_blocked_unassigned():
    assert rbac.has_permission("dr_smith", "ingest:all", "PT-9999") is False

def test_admin_no_clinical_access():
    assert rbac.has_permission("hia_admin", "query:all", "PT-0001") is False

def test_admin_can_read_audit():
    assert rbac.has_permission("hia_admin", "read:audit_log") is True

def test_nurse_cannot_lint():
    assert rbac.has_permission("nurse_jones", "lint:run", "PT-0001") is False

def test_require_raises_on_denied():
    with pytest.raises(PermissionError):
        rbac.require_permission("nurse_jones", "lint:run", "PT-0001")
