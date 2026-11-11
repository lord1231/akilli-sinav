"""Create the first admin from environment variables; never expose this as a public API."""
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def main() -> None:
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    name = os.getenv("ADMIN_FULL_NAME", "Sistem Yöneticisi").strip()
    if not email or len(password) < 14:
        raise SystemExit("ADMIN_EMAIL ve en az 14 karakterli ADMIN_PASSWORD gerekli.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Bu e-posta ile kullanıcı zaten var.")
        db.add(User(email=email, password_hash=hash_password(password),
                    full_name=name, role="admin", is_active=True))
        db.commit()
    print("Yönetici hesabı oluşturuldu.")


if __name__ == "__main__":
    main()
