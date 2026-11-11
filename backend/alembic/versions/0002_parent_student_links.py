"""Add parent-student consent relationship."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_parent_student"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "parent_student_links" not in inspect(bind).get_table_names():
        op.create_table(
            "parent_student_links",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("parent_id", sa.Uuid(), nullable=False),
            sa.Column("student_id", sa.Uuid(), nullable=False),
            sa.Column("consent_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_id", "student_id", name="uq_parent_student"),
        )
        op.create_index("ix_parent_student_links_parent_id", "parent_student_links", ["parent_id"])
        op.create_index("ix_parent_student_links_student_id", "parent_student_links", ["student_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if "parent_student_links" in inspect(bind).get_table_names():
        op.drop_index("ix_parent_student_links_student_id", table_name="parent_student_links")
        op.drop_index("ix_parent_student_links_parent_id", table_name="parent_student_links")
        op.drop_table("parent_student_links")
