from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.routes import exams


class FakeDB:
    def __init__(self, fail_commit=False):
        self.committed = False
        self.fail_commit = fail_commit

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("commit failed")
        self.committed = True


class RecordingTasks:
    def __init__(self, db):
        self.db = db
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        assert self.db.committed, "E-posta DB commit tamamlanmadan kuyruğa alındı"
        self.tasks.append((func, args, kwargs))


def overdue_exam():
    return SimpleNamespace(
        status="published",
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        duration_minutes=30,
        title="Deneme sınavı",
        score=88,
    )


def test_expiry_notifications_are_queued_only_after_commit(monkeypatch):
    db = FakeDB()
    tasks = RecordingTasks(db)
    exam = overdue_exam()

    def finalize(_db, item):
        item.status = "completed"
        return 22, ["veli@example.com"]

    monkeypatch.setattr(exams, "finalize_exam", finalize)
    monkeypatch.setattr(exams, "send_exam_result_email", lambda *args: None)

    assert exams.expire_overdue_exams(db, [exam], tasks) == 1
    assert db.committed is True
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0][1][0] == "veli@example.com"


def test_expiry_commit_failure_does_not_queue_notifications(monkeypatch):
    db = FakeDB(fail_commit=True)
    tasks = RecordingTasks(db)
    exam = overdue_exam()

    def finalize(_db, item):
        item.status = "completed"
        return 22, ["veli@example.com"]

    monkeypatch.setattr(exams, "finalize_exam", finalize)

    with pytest.raises(RuntimeError, match="commit failed"):
        exams.expire_overdue_exams(db, [exam], tasks)
    assert tasks.tasks == []
