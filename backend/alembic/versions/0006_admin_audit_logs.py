"""Add minimal administrator audit trail."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_admin_audit_logs"
down_revision = "0005_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "admin_audit_logs" not in inspector.get_table_names():
        op.create_table(
            "admin_audit_logs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("actor_id", sa.Uuid(), nullable=True),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("resource_type", sa.String(length=80), nullable=False),
            sa.Column("resource_id", sa.String(length=80), nullable=True),
            sa.Column("summary", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    existing = {item["name"] for item in inspect(bind).get_indexes("admin_audit_logs")}
    for name, columns in (
        ("ix_admin_audit_logs_actor_id", ["actor_id"]),
        ("ix_admin_audit_logs_action", ["action"]),
        ("ix_admin_audit_logs_resource_type", ["resource_type"]),
        ("ix_admin_audit_logs_created_at", ["created_at"]),
    ):
        if name not in existing:
            op.create_index(name, "admin_audit_logs", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "admin_audit_logs" not in inspect(bind).get_table_names():
        return
    existing = {item["name"] for item in inspect(bind).get_indexes("admin_audit_logs")}
    for name in (
        "ix_admin_audit_logs_created_at",
        "ix_admin_audit_logs_resource_type",
        "ix_admin_audit_logs_action",
        "ix_admin_audit_logs_actor_id",
    ):
        if name in existing:
            op.drop_index(name, table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
