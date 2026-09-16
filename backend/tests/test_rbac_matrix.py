import pytest

from app.auth.rbac import CurrentUser, allowed_categories_for, chunk_is_visible_to, region_filter_for, retrieval_mongo_filter
from app.models.user import Role


def _user(role: str, region: str | None = None) -> CurrentUser:
    return CurrentUser(
        {
            "_id": "000000000000000000000001",
            "name": "Test",
            "email": "test@example.com",
            "role": role,
            "region": region,
            "status": "ACTIVE",
        }
    )


GENERAL = {"category": "GENERAL", "region": None, "status": "APPROVED"}
SOUTHERN = {"category": "REGIONAL", "region": "SOUTHERN", "status": "APPROVED"}
WESTERN = {"category": "REGIONAL", "region": "WESTERN", "status": "APPROVED"}
CONFIDENTIAL = {"category": "CONFIDENTIAL_INTERNAL", "region": None, "status": "APPROVED"}
PENDING_GENERAL = {"category": "GENERAL", "region": None, "status": "PENDING"}


def test_normal_user_knowledge_matrix():
    user = _user(Role.NORMAL.value)
    assert allowed_categories_for(user) == {"GENERAL"}
    assert chunk_is_visible_to(user, GENERAL) is True
    assert chunk_is_visible_to(user, SOUTHERN) is False
    assert chunk_is_visible_to(user, CONFIDENTIAL) is False


def test_regional_southern_knowledge_matrix():
    user = _user(Role.REGIONAL.value, "SOUTHERN")
    assert region_filter_for(user) == "SOUTHERN"
    assert chunk_is_visible_to(user, GENERAL) is True
    assert chunk_is_visible_to(user, SOUTHERN) is True
    assert chunk_is_visible_to(user, WESTERN) is False
    assert chunk_is_visible_to(user, CONFIDENTIAL) is False


def test_super_user_knowledge_matrix():
    user = _user(Role.SUPER.value)
    assert chunk_is_visible_to(user, GENERAL) is True
    assert chunk_is_visible_to(user, SOUTHERN) is True
    assert chunk_is_visible_to(user, WESTERN) is True
    assert chunk_is_visible_to(user, CONFIDENTIAL) is True


def test_admin_is_not_super_for_knowledge_retrieval():
    user = _user(Role.ADMIN.value)
    assert allowed_categories_for(user) == set()
    assert chunk_is_visible_to(user, CONFIDENTIAL) is False


def test_pending_chunks_are_not_visible_even_to_super_user():
    user = _user(Role.SUPER.value)
    assert chunk_is_visible_to(user, PENDING_GENERAL) is False


def test_admin_mongo_filter_is_none():
    assert retrieval_mongo_filter(_user(Role.ADMIN.value)) is None
