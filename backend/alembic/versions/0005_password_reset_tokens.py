"""Add single-use password reset tokens.

The initial schema migration uses current SQLAlchemy metadata, so on a fresh
install this table may already exist before this revision is reached.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_password_reset_tokens"
down_revision = "0004_exam_review_note"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "password_reset_tokens" not in inspector.get_table_names():
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    existing = {item["name"] for item in inspect(bind).get_indexes("password_reset_tokens")}
    indexes = [
        ("ix_password_reset_tokens_user_id", ["user_id"], False),
        ("ix_password_reset_tokens_token_hash", ["token_hash"], True),
        ("ix_password_reset_tokens_expires_at", ["expires_at"], False),
    ]
    for name, columns, unique in indexes:
        if name not in existing:
            op.create_index(name, "password_reset_tokens", columns, unique=unique)


def downgrade() -> None:
    bind = op.get_bind()
    if "password_reset_tokens" not in inspect(bind).get_table_names():
        return
    existing = {item["name"] for item in inspect(bind).get_indexes("password_reset_tokens")}
    for name in (
        "ix_password_reset_tokens_expires_at",
        "ix_password_reset_tokens_token_hash",
        "ix_password_reset_tokens_user_id",
    ):
        if name in existing:
            op.drop_index(name, table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
