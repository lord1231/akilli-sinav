# Akıllı Sınav

MEB müfredatına dayalı, Gemini API destekli ve mobil uyumlu sınav platformu.

## Teknoloji
- Python 3.12, FastAPI
- PostgreSQL 16, SQLAlchemy 2, Alembic
- Google Gemini API (yalnızca sunucu tarafında)
- Docker Compose
- Pytest ve GitHub Actions

## Kurulum
1. `.env.example` dosyasını `.env` olarak kopyalayın.
2. Güçlü bir `SECRET_KEY`, veritabanı parolası ve sunucu ortamında `GEMINI_API_KEY` tanımlayın.
3. `docker compose up --build` ile başlatın.
4. API belgeleri: `/docs`; web arayüzü: `/app/`; sağlık kontrolü: `/health`; DB kontrolü: `/health/ready`.
4. sınıf Sosyal Bilgiler ve 5. sınıf müfredat dosyalarını ayrı ayrı içe aktarın: `docker compose exec api python -m app.cli.import_curriculum data/curriculum/4-sosyal-bilgiler-meb-2018.json`, `docker compose exec api python -m app.cli.import_curriculum data/curriculum/5-matematik-tymm-2024.json`, `docker compose exec api python -m app.cli.import_curriculum data/curriculum/5-sosyal-bilgiler-tymm-2024.json`, `docker compose exec api python -m app.cli.import_curriculum data/curriculum/5-fen-bilimleri-tymm-2024.json` ve `docker compose exec api python -m app.cli.import_curriculum data/curriculum/5-turkce-tymm-2024.json` ve `docker compose exec api python -m app.cli.import_curriculum data/curriculum/5-ingilizce-tymm-2025.json` ve `docker compose exec api python -m app.cli.import_curriculum data/curriculum/5-dkab-tymm-2026.json`. 2024 dosyaları tarihsel TYMM kayıtlarıdır. 5. sınıf İngilizce dosyası, TYMM 2025 standart İngilizce programının resmî tema sayfalarına dayanır; açıklamalar beceri odaklı Türkçe özetlerdir. Çoklu Yabancı Dil Eğitim Modeli ayrı tutulur. 5. sınıf Din Kültürü ve Ahlak Bilgisi dosyası, 2026 kurul kararı ve uygulama takvimine göre eklenmiştir.
6. İlk yönetici hesabını oluşturmak için `.env` içinde `ADMIN_EMAIL`, en az 14 karakterli `ADMIN_PASSWORD` ve `ADMIN_FULL_NAME` belirleyin; ardından `docker compose exec api python -m app.cli.create_admin` komutunu çalıştırın. Yönetici parolasını kurulumdan sonra güvenli biçimde saklayın.

## Uygulanan API
- Veli kaydı: `POST /api/auth/register`
- Giriş: `POST /api/auth/login`
- Oturum profili: `GET /api/auth/me`
- Veli öğrenci hesabı oluşturma: `POST /api/auth/students` (açık veli onayı zorunlu)
- Veli öğrencilerini listeleme: `GET /api/auth/students`
- Gemini ile 25 soru üretme: `POST /api/exams/generate`
- Sınavları listeleme/görüntüleme: `GET /api/exams`, `GET /api/exams/{id}`
- Cevap kaydetme ve teslim: `POST /api/exams/{id}/answers/{exam_question_id}`, `POST /api/exams/{id}/submit`
- Sonuç ve açıklamalar: `GET /api/exams/{id}/results`
- Yönetici inceleme kuyruğu: `GET /api/exams/review-queue`; yayımlama: `POST /api/exams/{id}/approve`
- Veli başarı raporu: `GET /api/auth/students/{student_id}/progress`
- E-posta bildirimi: sınav tesliminden sonra SMTP ayarları tanımlıysa veliye otomatik bildirim

## Test
`cd backend && pip install -r requirements.txt && pytest -q`.
GitHub Actions, Python 3.12 ile testleri çalıştırır.

## Önemli durum
Mobil uyumlu web arayüzü, veli/öğrenci/yönetici ekranları, sınav akışı, yönetici soru incelemesi ve isteğe bağlı SMTP bildirim kodu eklenmiştir. Resmî MEB öğrenme çıktılarının tamamının aktarımı, canlı Gemini/SMTP doğrulaması ve bulut dağıtımı henüz tamamlanmamıştır. Müfredat kaynağı ve sürüm politikası için `docs/curriculum-sources.md` dosyasına bakın. Gemini sınav üretimi, veritabanında ilgili sınıfa ait ders/ünite/kazanım kaydı ve sunucu tarafında GEMINI_API_KEY gerektirir. Yapay zekâ soruları otomatik oluşturulsa da öğrencilere açılmadan önce öğretmen/yönetici incelemesi gerektirir.

## Güvenlik
- API anahtarlarını ve gerçek öğrenci verilerini Git'e yüklemeyin.
- Öğrenci hesaplarını yalnızca veli onayıyla oluşturun.
- Admin rolü açık kayıt endpoint'inden verilemez.
- Çocuk verileri için KVKK, veri minimizasyonu, saklama süresi ve veli hakları ayrıca işletilmelidir.
- MEB kazanımlarını resmî kaynak URL'si ve sürümüyle kaydedin; telifli soru bankalarını kopyalamayın.
