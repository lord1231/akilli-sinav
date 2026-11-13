from pathlib import Path

from app.cli.doctor import run_checks
from app.core.config import settings
from app.core.security import hash_password
from app.models import User
from app.services.curriculum_seed import seed_missing_curriculum

CURRICULUM_DIR = Path(__file__).resolve().parents[2] / "data" / "curriculum"


def by_name(checks):
    return {c.name: c for c in checks}


def cfg(**over):
    base = dict(SECRET_KEY="x" * 40, GEMINI_API_KEY="gercek-anahtar", SMTP_HOST="smtp.ornek.com",
                SMTP_FROM_EMAIL="no-reply@ornek.com", APP_BASE_URL="https://sinav.ornek.org", APP_ENV="production")
    base.update(over)
    return settings.model_copy(update=base)


def test_doctor_flags_every_missing_piece_on_empty_install(factory):
    c = by_name(run_checks(session_factory=factory, cfg=cfg(GEMINI_API_KEY="", SMTP_HOST="", SECRET_KEY="secret")))
    assert c["Veritabanı bağlantısı"].ok
    assert not c["Müfredat (ders ve kazanımlar)"].ok
    assert not c["Yönetici hesabı"].ok and "create_admin" in c["Yönetici hesabı"].detail
    assert not c["SECRET_KEY"].ok and c["SECRET_KEY"].required
    assert not c["GEMINI_API_KEY"].ok and not c["SMTP ayarları"].ok


def test_doctor_passes_on_a_ready_install(factory):
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    with factory() as db:
        db.add(User(email="a@ornek.com", password_hash=hash_password("GucluParola12345"), full_name="Y", role="admin"))
        db.commit()
    checks = run_checks(session_factory=factory, cfg=cfg())
    c = by_name(checks)
    for name in ("Veritabanı bağlantısı", "Müfredat (ders ve kazanımlar)", "Yönetici hesabı", "SECRET_KEY",
                 "GEMINI_API_KEY", "SMTP ayarları", "APP_BASE_URL (HTTPS, gerçek alan adı)"):
        assert c[name].ok, f"{name}: {c[name].detail}"
    assert "882 kazanım" in c["Müfredat (ders ve kazanımlar)"].detail
    assert not any(x.required and not x.ok for x in checks if x.name != "Veritabanı migration'ları")


def test_doctor_smtp_test_sends_one_mail_and_reports_failures(factory, monkeypatch):
    sent = []
    monkeypatch.setattr("app.services.email.send_test_email", lambda to: sent.append(to))
    ok = by_name(run_checks(session_factory=factory, cfg=cfg(), smtp_test="ben@ornek.com"))["SMTP test e-postası"]
    assert ok.ok and sent == ["ben@ornek.com"]

    def boom(to):
        raise OSError("bağlantı reddedildi")
    monkeypatch.setattr("app.services.email.send_test_email", boom)
    bad = by_name(run_checks(session_factory=factory, cfg=cfg(), smtp_test="ben@ornek.com"))["SMTP test e-postası"]
    assert not bad.ok and "bağlantı reddedildi" in bad.detail


def test_doctor_warns_when_proxy_ip_setting_is_missing(factory, monkeypatch):
    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    c = by_name(run_checks(session_factory=factory, cfg=cfg()))["Proxy IP ayarı (FORWARDED_ALLOW_IPS)"]
    assert not c.ok and not c.required
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")
    assert by_name(run_checks(session_factory=factory, cfg=cfg()))["Proxy IP ayarı (FORWARDED_ALLOW_IPS)"].ok


def test_doctor_explains_missing_tables_instead_of_claiming_connection_failure():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    bare = sessionmaker(bind=create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}))
    c = by_name(run_checks(session_factory=bare, cfg=cfg()))
    assert c["Veritabanı bağlantısı"].ok
    assert not c["Veritabanı tabloları"].ok and "alembic upgrade head" in c["Veritabanı tabloları"].detail


def test_doctor_reports_unreachable_database():
    def broken():
        raise OSError("sunucu yok")
    c = by_name(run_checks(session_factory=broken, cfg=cfg()))
    assert not c["Veritabanı bağlantısı"].ok and "DATABASE_URL" in c["Veritabanı bağlantısı"].detail
