import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_exam_result_email(to_email: str, exam_title: str, score: int,
                           correct: int, total: int) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.info("SMTP ayarları tanımlı değil; sınav sonucu e-postası gönderilmedi.")
        return
    message = EmailMessage()
    message["Subject"] = f"Akıllı Sınav - {exam_title} sonucu"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(
        f"Merhaba,\n\nÖğrencinizin '{exam_title}' sınavı tamamlandı.\n"
        f"Doğru cevap: {correct}/{total}\nPuan: {score}/100\n\n"
        "Ayrıntılı açıklamalar için Akıllı Sınav veli panelini ziyaret edebilirsiniz."
    )
    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Sınav sonucu e-postası gönderilemedi.")


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning("Parola sıfırlama e-postası gönderilemedi: SMTP ayarları eksik.")
        return
    message = EmailMessage()
    message["Subject"] = "Akıllı Sınav - Parola sıfırlama"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(
        "Parolanızı yenilemek için aşağıdaki bağlantıyı kullanın. "
        "Bağlantı 30 dakika geçerlidir ve yalnızca bir kez kullanılabilir.\n\n"
        f"{reset_url}\n\nBu isteği siz yapmadıysanız bu e-postayı dikkate almayın."
    )
    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Parola sıfırlama e-postası gönderilemedi.")


def send_test_email(to_email: str) -> None:
    """SMTP ayarlarını doğrulamak için tek bir test e-postası gönderir; hata durumunda istisna fırlatır."""
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP_HOST ve SMTP_FROM_EMAIL tanımlı değil.")
    message = EmailMessage()
    message["Subject"] = "Akıllı Sınav - SMTP test e-postası"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content("Bu e-posta, Akıllı Sınav SMTP ayarlarının çalıştığını doğrulamak için gönderildi.")
    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
