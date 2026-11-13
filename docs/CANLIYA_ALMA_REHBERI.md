# Akıllı Sınav – Canlıya Alma Rehberi

Bu rehber, projeyi sıfırdan çalışır ve kullanıma hazır hâle getirmek için **sizin** yapmanız gereken adımları sırayla anlatır.
Her adımın sonunda "Doğrulama" bölümü vardır; o kutu başarılı olmadan sonraki adıma geçmeyin.

> Her aşamada tek komutla genel durumu görebilirsiniz:
> `docker compose exec api python -m app.cli.doctor`
> ✅ = hazır, ⚠️ = önerilir, ❌ = mutlaka düzeltilmeli.

---

## 1. Kod GitHub'da hazır

Düzeltmeler `main` dalında birleştirilmiştir; ayrıca bir şey göndermeniz gerekmez. CI'ın üç işi (SQLite, PostgreSQL 16, ön yüz) yeşil olmalıdır:
GitHub → **Actions** sekmesi.

## 2. Sunucuyu kurun (tek komut)

**Gerekenler**
- Ubuntu 22.04/24.04 gibi bir Linux sunucu (VPS) ve **Docker + Docker Compose** kurulu olmalı: https://docs.docker.com/engine/install/
  (Küçük bir VPS beklenen yük için yeterli olmalıdır; ben yük testi yapmadım.)
- Bir **alan adı** ve DNS'te `A` kaydı: `sinav.alanadiniz.com` → sunucunun IP adresi.
- Sunucuda **80 ve 443 portları** açık olmalı (HTTPS sertifikası için).
- Elinizde hazır: **Gemini API anahtarı** (https://aistudio.google.com/apikey) ve **Gmail uygulama parolası** (Bölüm 5).

**Kurulum**
```bash
git clone https://github.com/lord1231/akilli-sinav.git
cd akilli-sinav
bash scripts/install.sh
```
Betik size şunları sorar: alan adı, yönetici e-postası, Gemini anahtarı (yazarken görünmez), SMTP bilgileri (varsayılan Gmail). Sonra kendisi:

1. Rastgele `SECRET_KEY`, veritabanı parolası ve yönetici parolası üretir; `.env` dosyasını yalnızca sizin okuyabileceğiniz izinle (`600`) yazar.
2. **HTTPS'i Caddy ile otomatik** kurar (sertifikayı alır ve yeniler), API portunu internete kapatır, gerçek kullanıcı IP'sini okuyacak şekilde ayarlar (**Bölüm 6'nın tamamı bununla yapılmış olur**).
3. Servisleri derler ve başlatır, API'nin hazır olmasını bekler.
4. **Yönetici hesabını oluşturur (Bölüm 3)**, yönetici parolasını sunucudaki `.env`'den siler ve size **bir kez** gösterir.
5. `doctor` denetimini çalıştırır.

> Hatalı girdide (ör. `https://` ile başlayan alan adı, boş Gemini anahtarı) betik hiçbir şey yazmadan nedenini söyleyerek durur.
> Mevcut bir `.env` varsa üzerine yazmaz; `--force` verirseniz eskisini yedekleyip yeniden yazar.
> Betiği Docker'a dokunmadan denemek için: `bash scripts/install.sh --env-only`

**Doğrulama:** Tarayıcıda `https://sinav.alanadiniz.com/app/` açılmalı ve yönetici e-postası/parolasıyla giriş yapabilmelisiniz.
Sertifika alınamazsa: `docker compose logs --tail=50 caddy` (genellikle DNS kaydı veya 80/443 portu sorunudur).

<details><summary>Elle kurulum (betiği kullanmak istemezseniz)</summary>

```bash
cp .env.example .env && nano .env
docker compose up -d --build
```
`.env` içinde en az şunlar gerekir: `SECRET_KEY` (≥32 karakter), `POSTGRES_PASSWORD`, `APP_BASE_URL` (gerçek https adresi), `GEMINI_API_KEY`, `SMTP_HOST`, `SMTP_FROM_EMAIL`.
Rastgele değer üretmek için: `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`.
HTTPS için `.env`'e `DOMAIN=sinav.alanadiniz.com`, `COMPOSE_PROFILES=https`, `API_BIND=127.0.0.1`, `FORWARDED_ALLOW_IPS=*` ekleyin.
Değerleri tek tırnak içinde yazın (`SMTP_PASSWORD='...'`).
</details>

## 3. Yönetici hesabını oluşturun

> `scripts/install.sh` bunu sizin için zaten yaptı. Yalnızca elle kurulum yaptıysanız veya betik "yönetici oluşturulamadı" dediyse gerekir.

```bash
docker compose exec api python -m app.cli.create_admin
```
(E-posta ve parolayı `.env` içindeki `ADMIN_*` değerlerinden alır.) Sonra tarayıcıdan giriş yapın.

**Neden gerekli:** Yapay zekâ ile üretilen her sınav, öğrenciye açılmadan önce bir yönetici tarafından incelenip onaylanır.
Yönetici yoksa öğrenciler hiçbir sınavı göremez.

**Doğrulama:** Giriş yapınca "Yönetici inceleme kuyruğu" bölümü görünmeli.

## 4. Gemini ile gerçek sınav deneyin

```bash
docker compose exec api python -m app.cli.doctor --live-gemini
```
`✅ Gemini canlı deneme` görmelisiniz. Sonra uygulamadan uçtan uca deneyin:

1. **Veli kaydı** olun → giriş yapın.
2. **Öğrenci oluşturun** (onay kutusunu işaretleyin, sınıf 4 veya 5).
3. **Yeni sınav hazırla:** Ders → Ünite → Kazanım seçin → "Gemini ile 25 soru hazırla" (10–40 sn sürebilir).
4. **Yönetici hesabıyla** giriş yapın → kuyruktaki 25 soruyu okuyun → **İncele ve yayımla**.
5. **Öğrenci hesabıyla** giriş yapın → sınava girin → cevaplayın → teslim edin.
6. Velinin panelinde **Sonucu gör** ve **Sonuç PDF indir** çalışmalı.

| Hata mesajı | Anlamı | Çözüm |
|---|---|---|
| `Gemini API anahtarı sunucu ortamında tanımlanmamış` (503) | Anahtar yok | `.env` → `GEMINI_API_KEY`, sonra `docker compose up -d` |
| `Gemini servisine ulaşılamadı` (503) | Anahtar geçersiz / kota / ağ | Anahtarı ve Google hesabınızın kotasını kontrol edin |
| `Gemini 25 yerine N soru üretti`, `aynı veya çok benzer soru` (502) | Model hatalı çıktı verdi | Tekrar deneyin; sürekliyse `GEMINI_MODEL` değerini değiştirin |
| `Kazanım öğrencinin sınıf düzeyiyle eşleşmiyor` (400) | 4. sınıf öğrenciye 5. sınıf kazanımı | Öğrencinin sınıfına uygun dersi seçin |

> Saatte en fazla 10 sınav üretilebilir (kötüye kullanım koruması).
> Maliyeti düşürmek için isterseniz `.env` içinde `REUSE_REVIEWED_QUESTIONS=true` yapın: onaylı havuzda öğrencinin görmediği 25 soru varsa Gemini çağrılmaz.

## 5. E-posta (SMTP)

Parola sıfırlama ve veliye sınav sonucu e-postaları buna bağlıdır. `.env` örneği (Gmail uygulama parolası ile):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=hesabiniz@gmail.com
SMTP_PASSWORD=16-haneli-uygulama-parolasi
SMTP_FROM_EMAIL=hesabiniz@gmail.com
```
Gmail için önce Google hesabında 2 adımlı doğrulamayı açıp "Uygulama parolaları" bölümünden parola üretin.
Port 465 kullanırsanız SSL otomatik seçilir. Başka bir sağlayıcı (Brevo, Mailgun, kurumsal posta) da olur.

```bash
docker compose up -d
docker compose exec api python -m app.cli.doctor --smtp-test kendi@adresiniz.com
```
**Doğrulama:** `✅ SMTP test e-postası` ve e-postanın gelen kutusuna (veya spam klasörüne) düşmesi.
Sonra giriş ekranında **Parolamı unuttum**'u deneyin; gelen bağlantı `APP_BASE_URL` ile başlamalı ve yeni parola formunu açmalı.

## 6. HTTPS ve gerçek kullanıcı IP'si

> **`scripts/install.sh` kullandıysanız bu bölüm zaten uygulanmıştır** (Caddy, `FORWARDED_ALLOW_IPS`, API portunun kapatılması). Yalnızca kendi proxy'nizi (Nginx, Cloudflare) kullanıyorsanız aşağıyı okuyun.

Siteyi doğrudan 8000 portundan değil, HTTPS veren bir proxy arkasından yayınlayın. En kolayı **Caddy** (sertifikayı kendisi alır):

```
# /etc/caddy/Caddyfile
sinav.alanadiniz.com {
    reverse_proxy 127.0.0.1:8000
}
```
`sudo systemctl reload caddy`

**Önemli – giriş sınırı:** Uygulama IP başına dakikada 5 giriş denemesine izin verir. Proxy arkasında bu ayar yapılmazsa
**tüm kullanıcılar tek IP sayılır** ve birkaç kişi aynı anda girince herkes kilitlenir. `.env` içine ekleyin:

```
FORWARDED_ALLOW_IPS=*
```
`*` yalnızca 8000 portu internete **kapalıysa** güvenlidir. Güvenlik duvarında kapatın:
```bash
sudo ufw allow 80,443/tcp && sudo ufw deny 8000/tcp && sudo ufw enable
```
Cloudflare kullanıyorsanız gerçek IP başlığı farklıdır; yönetim panelinden "Proxied" durumunu ve bu ayarı birlikte değerlendirin.

**Doğrulama:** `https://sinav.alanadiniz.com/app/` açılmalı; `doctor` çıktısında proxy satırı ✅ olmalı.

## 7. Telefon kontrolü (bunu yalnızca siz yapabilirsiniz)

Otomatik testler işlevi doğrular ama ekranın gerçek telefonda nasıl göründüğünü görmediler. Telefonunuzdan sırasıyla deneyin:

- [ ] Giriş, kayıt, **Parolamı unuttum** formu
- [ ] Öğrenci olarak sınav: 25 soru kaydırılabiliyor mu, şıklara parmakla rahat dokunuluyor mu?
- [ ] Süre sayacı üstte sabit kalıyor mu, klavye açılınca taşma var mı?
- [ ] Teslim, sonuç ekranı, **PDF indir**
- [ ] Yatay çevirince düzen bozuluyor mu?

Bozuk görünen ekranın fotoğrafını (hangi telefon/tarayıcı olduğunu yazarak) bana gönderirseniz düzeltirim.
Telefonun ana ekranına eklemek için tarayıcı menüsünden **Ana ekrana ekle** yeterlidir; uygulama simgesi (AS) ve tam ekran açılış için gerekli manifest hazırdır. Bunu gerçek telefonda ben deneyemedim, sonucu bana bildirin.

## 8. Yedekleme

```bash
# Günlük yedek
docker compose exec -T db pg_dump -U sinav_user akilli_sinav | gzip > yedek-$(date +%F).sql.gz

# Her gece 03:00 otomatik (crontab -e)
0 3 * * * cd /home/kullanici/akilli-sinav && docker compose exec -T db pg_dump -U sinav_user akilli_sinav | gzip > /home/kullanici/yedekler/yedek-$(date +\%F).sql.gz

# Geri yükleme
gunzip -c yedek-2026-11-14.sql.gz | docker compose exec -T db psql -U sinav_user akilli_sinav
```
Yedekleri sunucudan **başka bir yere** de kopyalayın. Geri yüklemeyi bir kez deneyerek yedeğin çalıştığından emin olun.

## 9. Müfredat içeriğini gözden geçirme

Yaptığım otomatik denetim (her yeni dosyada da çalışır): 21 dosyanın tamamında sınıf/ders/sürüm dolu, resmî `meb.gov.tr` kaynağı var, boş ünite yok, ünite içinde tekrarlı kod yok, 882 kazanım veritabanına eksiksiz geçiyor.

**Yapamadığım:** kazanım metinlerini MEB'in resmî PDF'leriyle kelime kelime karşılaştırmak (bu ortamdan MEB sitesine erişimim yok). Bunun için:
1. Bir öğretmenden veya sizden, her dersten 5–10 kazanımı rastgele seçip dosyadaki `source_url` bağlantısındaki resmî programla karşılaştırmasını isteyin.
2. Hatalı bir metin bulursanız iki yol vardır (ikisi de var olan kazanımı **günceller**, yenisini eklemez):
   - **Yönetici paneli:** "Toplu MEB müfredatı aktarımı" kutusuna yalnızca düzelttiğiniz üniteyi ve kazanımı içeren JSON'u yapıştırın. Kazanım, ünite adı ve kazanım koduyla eşleşir. Örnek:
     ```json
     {"grade_level":5,"subject_name":"Türkçe","curriculum_version":"TYMM 2024",
      "source_url":"https://tymm.meb.gov.tr/ogretim-programlari/ortaokul-turkce-dersi/6",
      "units":[{"name":"<ünite adı birebir>","order_no":1,
                "outcomes":[{"code":"T.5.1.1","description":"Düzeltilmiş metin"}]}]}
     ```
   - **Depodaki dosya (kalıcı yol):** `data/curriculum/<dosya>.json` içinde metni düzeltin, commit'leyin, sunucuda
     `docker compose exec api python -m app.cli.import_curriculum data/curriculum/<dosya>.json` çalıştırın.
3. Uygulama yeniden başlarken yalnızca **veritabanında hiç olmayan** dersler yüklenir; mevcut kayıtlarınız (düzeltmeleriniz dahil) otomatik olarak ezilmez.
   Ancak `python -m app.cli.import_all_curriculum` komutunu elle çalıştırırsanız dosyadaki metinler veritabanındakilerin üzerine yazılır; düzeltmelerinizi önce dosyaya da işleyin.

## 10. Kullanıma açmadan son kontrol listesi

- [ ] Pull request yeşil ve birleştirildi
- [ ] `docker compose exec api python -m app.cli.doctor --live-gemini --smtp-test ben@adresim.com` → hiç ❌ yok
- [ ] Gerçek bir sınav uçtan uca denendi (Bölüm 4)
- [ ] Telefonda denendi (Bölüm 7)
- [ ] HTTPS çalışıyor, 8000 portu dışarıya kapalı (Bölüm 6)
- [ ] Yedek alındı ve geri yükleme denendi (Bölüm 8)
- [ ] Parola sıfırlama e-postası geliyor (Bölüm 5)

## Sık karşılaşılan sorunlar

| Belirti | Neden | Çözüm |
|---|---|---|
| Ders listesi boş | Müfredat yüklenmemiş | `doctor` çalıştırın; `docker compose restart api` |
| Öğrenci "Sınav henüz yayımlanmadı" görüyor | Yönetici onaylamadı | Yönetici panelinde **İncele ve yayımla** |
| Birkaç kişi aynı anda giriş yapamıyor | Proxy IP ayarı yok | Bölüm 6 → `FORWARDED_ALLOW_IPS` |
| Öğrenci süre bitmeden uygulamayı kapattı | Teslim edilmemiş sınav | Sunucu, süre + 1 dk sonra sınavı kendisi sonuçlandırır; öğrenci sonucu listeden görür, veliye e-posta gider |
| `Production ortamında ... tanımlanmalı` hatasıyla açılmıyor | `.env` eksik/zayıf | Hata mesajı eksik değişkeni söyler; düzeltip `docker compose up -d` |
