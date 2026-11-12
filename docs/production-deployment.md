# Canlı Ortam Kurulum ve Güvenlik Kontrol Listesi

Bu belge, Akıllı Sınav API'sini internete açmadan önce gereken yapılandırmayı açıklar. Bu depo henüz bir sunucuya dağıtılmış değildir.

## 1. Zorunlu sunucu değişkenleri

Kök dizinde `.env` dosyası oluşturun. `.env.example` dosyasını kopyalayabilir, ancak örnek değerleri gerçek değerlerle değiştirmelisiniz.

- `APP_ENV=production`
- `APP_DEBUG=false`
- `SECRET_KEY`: en az 32 karakterli, rastgele ve yalnızca bu uygulama için üretilmiş bir değer
- `POSTGRES_PASSWORD`: güçlü ve benzersiz veritabanı parolası
- `GEMINI_API_KEY`: sunucu ortamında saklanan Gemini API anahtarı
- `APP_BASE_URL`: gerçek alan adınızın HTTPS adresi
- `SMTP_HOST`, `SMTP_FROM_EMAIL`: parola kurtarma ve veli bildirimleri için e-posta sunucusu
- SMTP kimlik doğrulaması kullanılıyorsa `SMTP_USERNAME` ve `SMTP_PASSWORD`

Örnek gizli anahtar üretimi:

```bash
openssl rand -hex 32
```

Gizli anahtarları sohbet mesajlarına, GitHub deposuna veya istemci tarafı JavaScript'e koymayın. `.env` dosyasını Git'e eklemeyin.

## 2. Ağ ve HTTPS

- API'yi doğrudan internete açık bir portla sunmayın; TLS sağlayan Nginx, Caddy veya yönetilen bir HTTPS ters vekilinin arkasında çalıştırın.
- Ters vekil aynı makinedeyse `API_PORT=127.0.0.1:8000` kullanarak Docker portunu yalnızca yerel arayüze bağlayın.
- PostgreSQL portunu internete açmayın. Compose dosyasında veritabanı için host portu yayımlanmamaktadır.
- HTTPS sertifikasının geçerli olduğunu ve ters vekilin HTTP isteklerini HTTPS'ye yönlendirdiğini doğrulayın.
- Üretimde Swagger/OpenAPI dokümantasyon uç noktaları kapalıdır. Güvenlik başlıkları ve API yanıtları için `no-store` önbellek politikası etkinleştirilir.

## 3. Başlatma

```bash
docker compose up -d --build
docker compose ps
```

API konteyneri başlangıçta Alembic migration'larını uygular. İlk yönetici hesabı için `.env` içinde `ADMIN_EMAIL`, en az 14 karakterli `ADMIN_PASSWORD` ve `ADMIN_FULL_NAME` belirleyin; sonra `docker compose exec api python -m app.cli.create_admin` komutunu yalnızca bir kez çalıştırın. Müfredatları topluca içe aktarmak için `docker compose exec api python -m app.cli.import_all_curriculum` komutunu kullanın. Hazır olma kontrolü:

```bash
curl https://GERCEK-ALAN-ADINIZ/health/ready
```

Yanıt `{"status":"ready","database":"connected"}` olmalıdır.

## 4. Yedekleme ve işletim

- PostgreSQL için günlük yedekleme, yedeklerin şifrelenmesi ve geri yükleme denemesi planlayın.
- Uygulama, veritabanı, ters vekil ve e-posta gönderim günlüklerini izleyin; parola sıfırlama tokenlarını ve öğrenci yanıtlarını günlüklerde tutmayın.
- Gemini API kullanımını, kota ve maliyet limitlerini izleyin.
- Bağımlılık ve Docker temel imajı güncellemelerini düzenli uygulayın.
- Veli kaydı IP başına saatte 5, Gemini sınav üretimi saatte 10 istekle sınırlandırılır. Çoklu API worker/replica kullanılırsa mevcut IP tabanlı hız sınırı deposu süreçler arasında paylaşılmaz; üretimde Redis tabanlı ortak limiter kullanın.

## 5. Yayına çıkış öncesi zorunlu kontroller

- Gerçek alan adı, HTTPS ve SMTP ile uçtan uca parola kurtarma testi.
- Yönetici hesabı için güvenli ilk kurulum ve erişim denetimi.
- Veli onayı, KVKK aydınlatma metni, veri saklama süresi, veri silme/erişim süreçleri ve hizmet sağlayıcı sözleşmelerinin hukuk/uyum incelemesi.
- Öğrenci, veli ve yönetici hesaplarıyla gerçek Android cihazda uçtan uca test.
- Yapay zekâ tarafından üretilen her sınavın öğrenciye açılmadan önce öğretmen/yönetici tarafından incelenmesi.
- Yedekten geri yükleme ve kesinti kurtarma denemesi.

Bu maddeler tamamlanmadan uygulama gerçek öğrenci verileriyle kullanılmamalıdır.
