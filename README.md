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
2. Gerçek ortamda `APP_ENV=production`, `APP_DEBUG=false`, güçlü `SECRET_KEY`, veritabanı parolası, `GEMINI_API_KEY`, HTTPS `APP_BASE_URL` ve SMTP bilgilerini tanımlayın. Yerel geliştirmede `APP_ENV=development` kullanın.
3. `docker compose up --build` ile başlatın.
4. Geliştirme ortamında API belgeleri `/docs` adresindedir; üretimde Swagger/OpenAPI kapalıdır. Web arayüzü `/app/`, sağlık kontrolü `/health`, veritabanı kontrolü `/health/ready` adresindedir.
5. Tüm resmî müfredat dosyalarını tek komutla içe aktarın: `docker compose exec api python -m app.cli.import_all_curriculum`.
6. İlk yönetici hesabını oluşturmak için `.env` içinde `ADMIN_EMAIL`, en az 14 karakterli `ADMIN_PASSWORD` ve `ADMIN_FULL_NAME` belirleyin; ardından `docker compose exec api python -m app.cli.create_admin` komutunu bir kez çalıştırın.

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
Mobil uyumlu web arayüzü, veli/öğrenci/yönetici ekranları, sınav akışı, yönetici soru incelemesi ve isteğe bağlı SMTP bildirim kodu eklenmiştir. 4. sınıf 2018 Fen Bilimleri PDF’sinin ünite dağılım tablosu 46 kazanım bildirirken metinde 43 ayrı kodlu kazanım listelenmektedir; içe aktarılan dosyada yalnızca doğrulanabilen 43 kod bulunur ve bu fark ayrıca incelenmelidir. 4. sınıf İngilizce için 2018 programı kullanılır; 2025 programı kademeli uygulanmaktadır. 4. sınıf Trafik Güvenliği için 2018 programı 2026-2027’de geçerlidir; 2025 TYMM programı 2027-2028’den itibaren uygulanacaktır. 4. sınıf Müzik, Görsel Sanatlar ve Beden Eğitimi ve Oyun için 2018 programları kullanılır; 2025 güncellemeleri kademeli uygulanmaktadır. Resmî MEB öğrenme çıktılarının tamamının aktarımı, canlı Gemini/SMTP doğrulaması ve bulut dağıtımı henüz tamamlanmamıştır. Müfredat kaynağı ve sürüm politikası için `docs/curriculum-sources.md` dosyasına bakın. Gemini sınav üretimi, veritabanında ilgili sınıfa ait ders/ünite/kazanım kaydı ve sunucu tarafında GEMINI_API_KEY gerektirir. Yapay zekâ soruları otomatik oluşturulsa da öğrencilere açılmadan önce öğretmen/yönetici incelemesi gerektirir.

## Güvenlik
- API anahtarlarını ve gerçek öğrenci verilerini Git'e yüklemeyin.
- Öğrenci hesaplarını yalnızca veli onayıyla oluşturun.
- Admin rolü açık kayıt endpoint'inden verilemez.
- Çocuk verileri için KVKK, veri minimizasyonu, saklama süresi ve veli hakları ayrıca işletilmelidir.
- MEB kazanımlarını resmî kaynak URL'si ve sürümüyle kaydedin; telifli soru bankalarını kopyalamayın.

## Canlıya geçiş

Canlı sunucuya dağıtım öncesi zorunlu yapılandırma, HTTPS, SMTP, yedekleme ve KVKK kontrolleri için [`docs/production-deployment.md`](docs/production-deployment.md) listesini izleyin. Uygulama henüz canlıya dağıtılmamıştır.
