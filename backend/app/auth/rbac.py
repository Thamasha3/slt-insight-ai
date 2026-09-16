"""
Role-based access control.

React may hide buttons. This module is what actually rejects unauthorized API calls.
Every protected route reloads the user from MongoDB so deactivation/role changes apply immediately.
"""

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_access_token
from app.database.connection import users_collection
from app.models.document import DocumentStatus, KnowledgeCategory
from app.models.user import Role, UserStatus

# auto_error=False so a missing Authorization header is 401, not FastAPI's default 403.
_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, doc: dict):
        self.id: str = str(doc["_id"])
        self.name: str = doc["name"]
        self.email: str = doc["email"]
        self.role: str = doc["role"]
        self.region: str | None = doc.get("region")
        self.status: str = doc["status"]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    doc = await users_collection().find_one({"_id": ObjectId(user_id)})
    if doc is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    if doc["status"] != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is not active (status: {doc['status']})",
        )

    return CurrentUser(doc)


def require_roles(*allowed_roles: Role):
    async def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in {role.value for role in allowed_roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return _dependency


def allowed_categories_for(user: CurrentUser) -> set[str]:
    """
    Knowledge categories this user may retrieve (Phase 7).

    Admin is NOT given Super-User knowledge access by default.
    See docs/ambiguities.md item 1.
    """
    if user.role == Role.NORMAL.value:
        return {KnowledgeCategory.GENERAL.value}
    if user.role == Role.REGIONAL.value:
        return {KnowledgeCategory.GENERAL.value, KnowledgeCategory.REGIONAL.value}
    if user.role == Role.SUPER.value:
        return {
            KnowledgeCategory.GENERAL.value,
            KnowledgeCategory.REGIONAL.value,
            KnowledgeCategory.CONFIDENTIAL_INTERNAL.value,
        }
    return set()


def region_filter_for(user: CurrentUser) -> str | None:
    """Regional users may only retrieve regional documents for this region."""
    if user.role == Role.REGIONAL.value:
        return user.region
    return None


def retrieval_mongo_filter(user: CurrentUser) -> dict | None:
    """
    MongoDB filter for permission-aware retrieval.

    Returns None when the role has no knowledge categories (Admin, until SLT
    defines Admin chat access). Callers must treat None as "return nothing".
    """
    categories = allowed_categories_for(user)
    if not categories:
        return None

    clauses: list[dict] = []
    if KnowledgeCategory.GENERAL.value in categories:
        clauses.append({"category": KnowledgeCategory.GENERAL.value})
    if KnowledgeCategory.REGIONAL.value in categories:
        allowed_region = region_filter_for(user)
        if allowed_region is not None:
            clauses.append(
                {"category": KnowledgeCategory.REGIONAL.value, "region": allowed_region}
            )
        else:
            clauses.append({"category": KnowledgeCategory.REGIONAL.value})
    if KnowledgeCategory.CONFIDENTIAL_INTERNAL.value in categories:
        clauses.append({"category": KnowledgeCategory.CONFIDENTIAL_INTERNAL.value})

    return {"status": DocumentStatus.APPROVED.value, "$or": clauses}


def chunk_is_visible_to(user: CurrentUser, chunk: dict) -> bool:
    """
    Server-side retrieval gate. Wired into RAG in Phase 7.

    A chunk is visible only if:
    - its parent document has been APPROVED (not PENDING/REJECTED/FAILED)
    - its category is in the user's allowed set
    - if it is REGIONAL, the user's region matches (Super User: any region)
    """
    if chunk.get("status") != DocumentStatus.APPROVED.value:
        return False
    category = chunk.get("category")
    if category not in allowed_categories_for(user):
        return False
    if category == KnowledgeCategory.REGIONAL.value:
        allowed_region = region_filter_for(user)
        if allowed_region is not None and chunk.get("region") != allowed_region:
            return False
    return True
