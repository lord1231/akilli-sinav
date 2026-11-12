"""Store the administrator's exam review rejection note."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_exam_review_note"
down_revision = "0003_subject_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in inspect(op.get_bind()).get_columns("exams")}
    if "review_note" not in columns:
        op.add_column("exams", sa.Column("review_note", sa.Text(), nullable=True))


def downgrade() -> None:
    columns = {item["name"] for item in inspect(op.get_bind()).get_columns("exams")}
    if "review_note" in columns:
        op.drop_column("exams", "review_note")
