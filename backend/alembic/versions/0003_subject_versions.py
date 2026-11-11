"""Allow multiple curriculum versions for the same grade and subject."""

from alembic import op
from sqlalchemy import inspect

revision = "0003_subject_versions"
down_revision = "0002_parent_student"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    constraints = inspect(bind).get_unique_constraints("subjects")
    names = {item.get("name") for item in constraints}
    if "uq_subject_grade_name_version" not in names:
        with op.batch_alter_table("subjects") as batch:
            if "uq_subject_grade_name" in names:
                batch.drop_constraint("uq_subject_grade_name", type_="unique")
            batch.create_unique_constraint(
                "uq_subject_grade_name_version",
                ["grade_level", "name", "curriculum_version"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    constraints = inspect(bind).get_unique_constraints("subjects")
    names = {item.get("name") for item in constraints}
    if "uq_subject_grade_name" not in names:
        with op.batch_alter_table("subjects") as batch:
            if "uq_subject_grade_name_version" in names:
                batch.drop_constraint("uq_subject_grade_name_version", type_="unique")
            batch.create_unique_constraint("uq_subject_grade_name", ["grade_level", "name"])
