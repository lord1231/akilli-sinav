"""Add a fixed duration to exams."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_exam_duration"
down_revision = "0006_admin_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in inspect(bind).get_columns("exams")}
    if "duration_minutes" not in columns:
        op.add_column(
            "exams",
            sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in inspect(bind).get_columns("exams")}
    if "duration_minutes" in columns:
        op.drop_column("exams", "duration_minutes")
