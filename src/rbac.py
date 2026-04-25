"""
Role-Based Access Control (RBAC) for HIPAA-LLM-Wiki.
Loads config/roles.yaml and enforces patient-scoped access.
"""
from __future__ import annotations
import yaml
from pathlib import Path
from typing import Optional
from src.audit import audit_log_access_denied


ROLES_FILE = Path("config/roles.yaml")


def _load_config() -> dict:
    if not ROLES_FILE.exists():
        raise FileNotFoundError(f"Roles config not found: {ROLES_FILE}")
    with ROLES_FILE.open() as f:
        return yaml.safe_load(f)


def get_user(username: str) -> Optional[dict]:
    cfg = _load_config()
    for user in cfg.get("users", []):
        if user["username"] == username and user.get("active", True):
            return user
    return None


def get_role(role_name: str) -> Optional[dict]:
    cfg = _load_config()
    return cfg.get("roles", {}).get(role_name)


def has_permission(username: str, permission: str, patient_id: Optional[str] = None) -> bool:
    """
    Check whether a user has a given permission, optionally scoped to a patient.

    Permissions follow the format "action:scope", e.g.:
        read:all, write:wiki, ingest:all, query:all, lint:run
    """
    user = get_user(username)
    if not user:
        return False

    role = get_role(user["role"])
    if not role:
        return False

    perms: list[str] = role.get("permissions", [])

    # Check direct permission or wildcard
    matched = permission in perms or f"{permission.split(':')[0]}:all" in perms

    if not matched:
        return False

    # Enforce patient scope
    if patient_id:
        scope = role.get("patient_scope", "assigned_only")
        if scope == "assigned_only":
            assigned = user.get("assigned_patients", [])
            if patient_id not in assigned:
                return False
        elif scope == "none":
            return False
        # "all" or "deidentified_only" — allow (caller handles de-id)

    return True


def require_permission(username: str, permission: str, patient_id: Optional[str] = None) -> None:
    """Raise PermissionError (and audit-log) if access is denied."""
    if not has_permission(username, permission, patient_id):
        reason = f"Permission denied: {permission} on {patient_id or 'N/A'}"
        audit_log_access_denied(username, patient_id or "N/A", reason)
        raise PermissionError(reason)


def list_accessible_patients(username: str) -> list[str]:
    """Return the list of patient_ids the user may access."""
    user = get_user(username)
    if not user:
        return []
    role = get_role(user["role"])
    if not role:
        return []
    scope = role.get("patient_scope", "assigned_only")
    if scope == "all":
        # Return all patient folders that exist
        return [p.name for p in Path("wiki").iterdir() if p.is_dir()]
    elif scope == "assigned_only":
        return user.get("assigned_patients", [])
    return []
