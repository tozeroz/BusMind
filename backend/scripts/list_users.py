"""List existing users in the MySQL user_account table.

Run with the backend's own .env loaded:

    cd backend
    python scripts/list_users.py
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    with SessionLocal() as db:
        rows = db.execute(
            select(
                User.user_id,
                User.username,
                User.nickname,
                User.role,
                User.status,
                User.created_at,
                User.last_login_at,
            )
            .order_by(User.created_at.desc())
        ).all()

        if not rows:
            print("(no users yet — register one via POST /api/v1/users/register)")
            return

        print(f"-- {len(rows)} user(s) in user_account --")
        for row in rows:
            last = row.last_login_at.isoformat() if row.last_login_at else "—"
            print(
                f"  id={row.user_id}  username={row.username}  "
                f"nickname={row.nickname or '—'}  role={row.role}  "
                f"status={row.status}  created={row.created_at}  last_login={last}"
            )


if __name__ == "__main__":
    main()