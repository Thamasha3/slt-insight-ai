"""
Create the first Admin account.

Self-registration cannot create ADMIN. Run this once after MongoDB is up:

    cd backend
    .venv\\Scripts\\activate
    python scripts/bootstrap_admin.py

The email MUST match ADMIN_EMAIL_1 or ADMIN_EMAIL_2 in .env.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth.security import hash_password
from app.config.settings import get_settings
from app.database.connection import close_mongo_connection, connect_to_mongo, users_collection
from app.models.user import Role, UserStatus, new_user_document


async def main() -> None:
    connect_to_mongo()
    settings = get_settings()
    email = settings.admin_email_1.strip().lower()

    existing = await users_collection().find_one({"email": email})
    if existing:
        print(f"An account already exists for {email}. Nothing to do.")
        close_mongo_connection()
        return

    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe123")
    document = new_user_document(
        name="System Administrator",
        email=email,
        password_hash=hash_password(password),
        role=Role.ADMIN,
        region=None,
        status=UserStatus.ACTIVE,
    )
    await users_collection().insert_one(document)
    print(f"Created ADMIN account for {email}.")
    print("Log in with that email and the password from BOOTSTRAP_ADMIN_PASSWORD (default: ChangeMe123).")
    print("Change the password after first login in a later phase, or reset it in MongoDB.")
    close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
