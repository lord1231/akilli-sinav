# MEB müfredat kaynakları ve veri giriş standardı

Son kontrol: 12 Kasım 2026. Bu belge, kaynak envanteridir; resmî programların yerine geçmez.

## 2026-2027 uygulama notu

MEB Türkiye Yüzyılı Maarif Modeli temel eğitim taslak yıllık planları sayfası, 2026-2027 yılında modelin 1, 2, 3, 5, 6 ve 7. sınıflarda uygulanacağını belirtir. Bu nedenle 4. sınıfı tüm dersler için otomatik olarak TYMM kabul etmeyin. 4. sınıfta ders bazında yürürlükteki program ve varsa özel güncelleme ayrıca doğrulanmalıdır.

Resmî kaynaklar:
- TYMM temel eğitim taslak yıllık planları: https://tymm.meb.gov.tr/taslak-cerceve-planlari/temel-egitim
- TTKB öğretim programları kataloğu: https://mufredat.meb.gov.tr/Programlar.aspx
- TYMM program arayüzü: https://tymm.meb.gov.tr/ogretim-programlari

## Doğrulanmış örnek program kayıtları

| Ders | Sınıf kapsamı | Resmî program kaydı |
|---|---:|---|
| Ortaokul Matematik | 5-8 | TYMM 2024, PID 1978 |
| Ortaokul Türkçe | 5-8 | TYMM 2024, PID 1979 |
| Sosyal Bilgiler | 4-7 | TYMM 2024, PID 1981 |

Program ayrıntıları:
- Matematik: https://mufredat.meb.gov.tr/ProgramDetay.aspx?PID=1978
- Türkçe: https://mufredat.meb.gov.tr/ProgramDetay.aspx?PID=1979
- Sosyal Bilgiler: https://mufredat.meb.gov.tr/ProgramDetay.aspx?PID=1981
- Matematik PDF: https://mufredat.meb.gov.tr/Dosyalar/202582516434252-ortaokul%20matematik.pdf
- Sosyal Bilgiler PDF: https://mufredat.meb.gov.tr/Dosyalar/202582516728345-sosyal%20bilgiler.pdf

5. sınıf matematik programında altı tema yer alır: Sayılar ve Nicelikler, İşlemlerle Cebirsel Düşünme, Geometrik Şekiller, Geometrik Nicelikler, İstatistiksel Araştırma Süreci ve Veriden Olasılığa. Sosyal Bilgiler programı 4. sınıfta ve 5. sınıfta ayrı öğrenme alanları tanımlar.

## 12 Kasım 2026 katalog kontrolü: sürüm uyuşmazlığı uyarısı

TTKB katalog arama görünümünde bazı temel eğitim dersleri için 2026 tarihli kayıtlar görünmektedir: İlkokul Türkçe (1-4), İlkokul Matematik (1-4), Fen Bilimleri (3-8), Ortaokul Matematik (5-8), Ortaokul Türkçe (5-8) ve Sosyal Bilgiler (4-7). Din Kültürü ve Ahlak Bilgisi için de 2026 programı listelenmektedir.

Ancak katalog sayfasının önbelleğe alınmış metin görünümü bazı derslerde yalnızca 2024 sürümünü göstermektedir. Bu nedenle arama görünümünde görülen kayıtlar ile açılabilen program/PDF sürümü birebir eşleştirilmeden 2026 programına ait PID, kazanım kodu veya yürürlük tarihi varsayılmayacaktır.

- Güncel katalog: https://mufredat.meb.gov.tr/Programlar.aspx
- TYMM program portalı: https://tymm.meb.gov.tr/ogretim-programlari
- Ayrıntılı sınıf/ders takip listesi: `docs/curriculum-roadmap-2026-2027.md`

**Din Kültürü ve Ahlak Bilgisi yürürlük notu:** 2026 programına ilişkin kurul kararında 2026-2027 yılında 5, 6 ve 7. sınıflarda; 2027-2028 yılında tüm sınıf seviyelerinde uygulanacağı belirtilmektedir. Bu nedenle 4. sınıf için 2026 programı 2026-2027 yılında etkinleştirilmez. Resmî karar/PDF: https://dogm.meb.gov.tr/Programlar/Ortaokul/2026004-Dkab-orta.pdf

**Veri güvenliği:** Depodaki `5-matematik-tymm-2024.json` ve `5-sosyal-bilgiler-tymm-2024.json` dosyaları tarihsel 2024 kayıtlarıdır. Yeni programın resmî PDF'si, öğrenme çıktıları ve yürürlük takvimi doğrulanmadan eski dosyalar güncel program olarak işaretlenmeyecek ve yeni sürüm adına tahmini kazanım eklenmeyecektir.

## Sisteme veri girme kuralları

1. Ders, sınıf seviyesi ve müfredat sürümü birlikte kaydedilir.
2. Ünite/tema adı, kazanım/öğrenme çıktısı kodu ve açıklaması resmî programdan doğrulanır.
3. Her öğrenme çıktısına resmî MEB kaynak URL'si ve sürüm bilgisi eklenir.
4. Programdaki kod ve açıklama aynen doğrulanmadan yapay zekâya soru ürettirilmez.
5. Telifli soru bankaları, ders kitabı soruları veya yayımlanmış örnek sorular kopyalanmaz. Sistem yalnızca doğrulanmış öğrenme çıktısına dayalı özgün soru üretir.
6. Program değiştiğinde eski sürüm silinmez; yeni sürüm ayrı kaydedilir ve eski sınavların hangi sürümle üretildiği korunur.
7. Yeni programın yürürlük tarihi ve sınıf kapsamı resmî MEB duyurusundan kontrol edilmeden otomatik etkinleştirme yapılmaz.

## Depoda hazır içe aktarım dosyaları

- `data/curriculum/5-matematik-tymm-2024.json`: 5. sınıf Matematik, 6 tema ve 23 öğrenme çıktısı.
- `data/curriculum/5-sosyal-bilgiler-tymm-2024.json`: 5. sınıf Sosyal Bilgiler, 6 öğrenme alanı ve 19 öğrenme çıktısı.

Bu iki dosya, yukarıdaki resmî MEB PDF programlarından alınan öğrenme çıktısı kodları ve kısa resmî açıklamalarla hazırlanmıştır. `backend/app.cli.import_curriculum` komutuyla veritabanına yüklenebilir.

## Veri durumunun dürüst gösterimi

Bu depoda müfredat yönetim API'si ve yönetici veri giriş ekranı bulunur. Resmî öğrenme çıktılarının tamamı henüz veri tabanına aktarılmış değildir. Bu nedenle ders listesi boşsa sistemin eksik veri durumu saklanmamalı; yönetici önce resmî kaynaktan veri girmelidir. Eksik veya tahmin edilmiş kazanımlarla sınav üretimi yapılmamalıdır.
