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

## Sisteme veri girme kuralları

1. Ders, sınıf seviyesi ve müfredat sürümü birlikte kaydedilir.
2. Ünite/tema adı, kazanım/öğrenme çıktısı kodu ve açıklaması resmî programdan doğrulanır.
3. Her öğrenme çıktısına resmî MEB kaynak URL'si ve sürüm bilgisi eklenir.
4. Programdaki kod ve açıklama aynen doğrulanmadan yapay zekâya soru ürettirilmez.
5. Telifli soru bankaları, ders kitabı soruları veya yayımlanmış örnek sorular kopyalanmaz. Sistem yalnızca doğrulanmış öğrenme çıktısına dayalı özgün soru üretir.
6. Program değiştiğinde eski sürüm silinmez; yeni sürüm ayrı kaydedilir ve eski sınavların hangi sürümle üretildiği korunur.
7. Yeni programın yürürlük tarihi ve sınıf kapsamı resmî MEB duyurusundan kontrol edilmeden otomatik etkinleştirme yapılmaz.

## Veri durumunun dürüst gösterimi

Bu depoda müfredat yönetim API'si ve yönetici veri giriş ekranı bulunur. Resmî öğrenme çıktılarının tamamı henüz veri tabanına aktarılmış değildir. Bu nedenle ders listesi boşsa sistemin eksik veri durumu saklanmamalı; yönetici önce resmî kaynaktan veri girmelidir. Eksik veya tahmin edilmiş kazanımlarla sınav üretimi yapılmamalıdır.
