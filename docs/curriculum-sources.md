# MEB müfredat kaynakları ve veri giriş standardı

Son kontrol: 12 Kasım 2026. Bu belge resmî programların yerine geçmez; kaynak ve sürüm envanteridir.

## 2026-2027 uygulama notu

TYMM'nin genel uygulama kapsamı 2026-2027 yılında 1, 2, 3, 5, 6 ve 7. sınıflardır. 4. sınıfta mevcut programlar devam eder. Ders bazlı güncellemeler ayrıca kontrol edilmelidir.

Resmî kaynaklar:
- TTKB kataloğu: https://mufredat.meb.gov.tr/Programlar.aspx
- TYMM temel eğitim planları: https://tymm.meb.gov.tr/taslak-cerceve-planlari/temel-egitim
- TTKB SSS: https://ttkb.meb.gov.tr/www/sss.php

## Eklenen 4. sınıf kaydı

### Sosyal Bilgiler — MEB 2018

Resmî 2018 programının 4. sınıf kazanımları yedi öğrenme alanında 33 kayıt olarak data/curriculum/4-sosyal-bilgiler-meb-2018.json dosyasına aktarılmıştır: Birey ve Toplum; Kültür ve Miras; İnsanlar, Yerler ve Çevreler; Bilim, Teknoloji ve Toplum; Üretim, Dağıtım ve Tüketim; Etkin Vatandaşlık; Küresel Bağlantılar.

Kaynak PDF: https://mufredat.meb.gov.tr/Dosyalar/201812103847686-SOSYAL%20B%C4%B0LG%C4%B0LER%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI%20.pdf

## 4. sınıf için diğer resmî kaynaklar

- Türkçe 2019: https://mufredat.meb.gov.tr/Dosyalar/20195716392253-02-T%C3%BCrk%C3%A7e%20%C3%96%C4%9Fretim%20Program%C4%B1%202019.pdf
- Matematik 2018: https://mufredat.meb.gov.tr/Dosyalar/201813017165445-MATEMAT%C4%B0K%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI%202018v.pdf
- Fen Bilimleri 2018: https://mufredat.meb.gov.tr/Dosyalar/201812312311937-FEN%20B%C4%B0L%C4%B0MLER%C4%B0%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI2018.pdf
- İngilizce 2025 güncellemesi: https://ttkb.meb.gov.tr/www/ingilizce-dersi-ogretim-programlarinda-guncelleme-yapildi/icerik/795
- İngilizce 4. sınıf portalı: https://tymm.meb.gov.tr/ogretim-programlari/ingilizce-dersi-temel-egitim/5
- DKAB 2026: https://mufredat.meb.gov.tr/Dosyalar/202631310725635-dkab48.pdf
- Trafik Güvenliği 4. sınıf: https://tymm.meb.gov.tr/ogretim-programlari/ders/trafik-guvenligi-dersi

**DKAB yürürlük ayrımı:** 2026 DKAB programı 2026-2027'de 5, 6 ve 7. sınıflarda; tüm sınıf seviyelerinde 2027-2028'de uygulanacaktır. Bu nedenle 2026-2027 4. sınıf veri seti olarak 2026 programı kullanılmamalıdır.

## 5. sınıf program kayıtları

- Matematik TYMM 2024: https://mufredat.meb.gov.tr/ProgramDetay.aspx?PID=1978
- Türkçe TYMM 2024: https://mufredat.meb.gov.tr/ProgramDetay.aspx?PID=1979
- Sosyal Bilgiler TYMM 2024: https://mufredat.meb.gov.tr/ProgramDetay.aspx?PID=1981
- İngilizce 5. sınıf: https://tymm.meb.gov.tr/ogretim-programlari/ingilizce-dersi-temel-egitim/6
- DKAB 2026: https://dogm.meb.gov.tr/Programlar/Ortaokul/2026004-Dkab-orta.pdf

## Veri giriş kuralları

1. Ders, sınıf seviyesi, sürüm ve yürürlük yılı birlikte kaydedilir.
2. Ünite/tema, kazanım kodu ve açıklama resmî kaynaktan doğrulanır.
3. Her veri dosyası resmî HTTPS MEB kaynağına işaret eder.
4. Telifli soru bankaları veya ders kitabı soruları kopyalanmaz; doğrulanmış kazanımlardan özgün soru üretilir.
5. Program değişince eski sürüm silinmez; yeni sürüm ayrı dosya olarak eklenir.
6. Yürürlük tarihi kesinleşmeden otomatik sınav üretimi etkinleştirilmez.

## Veri envanteri

- data/curriculum/4-sosyal-bilgiler-meb-2018.json: 4. sınıf Sosyal Bilgiler, 7 öğrenme alanı ve 33 kazanım.
- data/curriculum/5-matematik-tymm-2024.json
- data/curriculum/5-sosyal-bilgiler-tymm-2024.json
- data/curriculum/5-fen-bilimleri-tymm-2024.json
- data/curriculum/5-turkce-tymm-2024.json
- data/curriculum/5-ingilizce-tymm-2025.json
- data/curriculum/5-dkab-tymm-2026.json