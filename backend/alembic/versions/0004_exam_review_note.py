"""Store the administrator's exam review rejection note."""

from alembic import op
import sqlalchemy as sa

revision = "0004_exam_review_note"
down_revision = "0003_subject_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("review_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("exams", "review_note")
