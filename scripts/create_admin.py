"""Create (or promote) an admin. Run: python -m scripts.create_admin admin@example.com 'StrongPassword' 'Admin Name'"""
import os
import sys

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Role
from app.repositories import users as users_repo


def main(email: str, password: str, name: str = "Administrator") -> None:
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters")
    with SessionLocal() as db:
        user = users_repo.get_by_email(db, email)
        if user:
            user.role, user.is_active = Role.admin, True
            db.commit()
            print(f"Promoted existing user {email} to admin")
        else:
            users_repo.create(db, name=name, email=email.lower(), phone=None, password_hash=hash_password(password), role=Role.admin)
            print(f"Created admin {email}")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        main(*sys.argv[1:4])
    elif os.environ.get("ADMIN_EMAIL") and os.environ.get("ADMIN_PASSWORD"):
        main(os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"], os.environ.get("ADMIN_NAME", "Administrator"))
    else:
        sys.exit(__doc__)
