from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, String, TEXT, text
from sqlalchemy.sql import func

from app.db.base import BIGINT_COMPAT, Base


class User(Base):
    """ORM mapping for database table ``user_account``."""

    __tablename__ = "user_account"

    user_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=True)
    role = Column(String(20), nullable=False, default="passenger", server_default=text("'passenger'"), index=True)
    status = Column(String(20), nullable=False, default="active", server_default=text("'active'"), index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)


class QueryHistory(Base):
    """ORM mapping for database table ``user_query_history``."""

    __tablename__ = "user_query_history"

    history_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=True)
    user_id = Column(
        BIGINT_COMPAT,
        ForeignKey("user_account.user_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    query_type = Column(String(30), nullable=False, index=True)
    origin_name = Column(String(100), nullable=True)
    origin_longitude = Column(DECIMAL(10, 7), nullable=True)
    origin_latitude = Column(DECIMAL(10, 7), nullable=True)
    destination_name = Column(String(100), nullable=True)
    destination_longitude = Column(DECIMAL(10, 7), nullable=True)
    destination_latitude = Column(DECIMAL(10, 7), nullable=True)
    selected_route_id = Column(BIGINT_COMPAT, nullable=True)
    query_content = Column(TEXT, nullable=True)
    result_summary = Column(TEXT, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    @property
    def query_params(self) -> str | None:
        """Backward-compatible alias used by the existing API schema."""

        return self.query_content

    @query_params.setter
    def query_params(self, value: str | None) -> None:
        self.query_content = value


# Re-export Base so legacy imports such as ``from app.models.user import Base``
# continue to work while all models share the same metadata.
__all__ = ["Base", "User", "QueryHistory", "UserFavorite"]

# Legacy import compatibility. Favorites are represented by reserved records in
# user_query_history; this alias does not create an extra database table.
UserFavorite = QueryHistory
