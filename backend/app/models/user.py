"""User domain: four roles, account statuses, sample regions."""

from datetime import datetime, timezone
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    SUPER = "SUPER"
    REGIONAL = "REGIONAL"
    NORMAL = "NORMAL"


class UserStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    DEACTIVATED = "DEACTIVATED"


class Region(StrEnum):
    """Sample regions only — replace with SLT's official list when provided."""

    WESTERN = "WESTERN"
    SOUTHERN = "SOUTHERN"
    NORTHERN = "NORTHERN"
    EASTERN = "EASTERN"
    CENTRAL = "CENTRAL"


def new_user_document(
    name: str,
    email: str,
    password_hash: str,
    role: Role,
    region: str | None,
    status: UserStatus,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "role": role.value,
        "region": region,
        "status": status.value,
        "created_at": now,
        "updated_at": now,
    }
