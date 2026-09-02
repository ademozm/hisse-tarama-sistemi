# Çoklu Piyasa Hisse/Kripto Tarama ve Analiz Sistemi

Gün içi birden fazla kez çalışabilen, ABD hisseleri + BIST + kripto
paraları tarayan, rejim-uyarlamalı (trend/yatay) sinyal üreten, sonuçları
skorlayıp Excel raporu olarak sunan uçtan uca bir sistem.

## 🖱️ Tarayıcıda Görsel Panel (terminal komutu yazmadan kullanmak için)

Kurulumu bir kere yaptıktan sonra (aşağıdaki "Kurulum" bölümü), her
seferinde terminale komut yazmak yerine:

- **Windows:** `uygulamayi_baslat.bat` dosyasına **çift tıkla**
- **Mac:** `uygulamayi_baslat.command` dosyasına çift tıkla (ilk seferinde
  sağ tık → "Aç" demen gerekebilir, Mac güvenlik uyarısı verir)

Birkaç saniye sonra tarayıcında (Chrome/Edge) otomatik bir sekme açılır.
Bu artık sadece bir tablo değil, **gerçek bir görsel panel**:

- **KPI kartları**: toplam sinyal, AL/SAT sayısı, ortalama skor, şüpheli
  veri sayısı, yaklaşan önemli ekonomik olay sayısı — bir bakışta özet
- **📊 Genel Bakış sekmesi**: piyasa dağılımı (pasta grafik), skor
  dağılımı (histogram), en iyi 10 AL/SAT (çubuk grafik)
- **📈 Grafik İnceleme sekmesi**: istediğin sembolü seç, interaktif mum
  grafiği + EMA çizgileri + destek/direnç seviyeleri + hacim grafiği
  açılsın
- **💼 Piyasalar, 🔬 Temel & Risk & Gelişmiş, ⚠️ Hata Raporu**: detaylı
  tablolar, renk skalalı skorlar
- **🎯 Grid & DCA sekmesi**: grid seviyelerini merdiven grafiğinde, DCA
  planını basamaklı çizgide gör
- **📰 Haberler sekmesi**: renkli ton göstergeli haber kartları
- **📅 Ekonomik Takvim sekmesi**: yaklaşan Fed/NFP/CPI olayları kart
  görünümünde
- **📜 Geçmiş Performans sekmesi**: sinyallerin zaman içindeki başarı
  istatistikleri

Excel dosyasını da aynı sayfadan indirebilirsin — panel, Excel'in
YERİNE değil, ONA EK bir görselleştirme katmanı.

Kapatmak için tarayıcı sekmesini kapat, sonra açılan siyah pencereyi de
kapatabilirsin (veya bir tuşa basıp devam et).

## Mimari v2 — Tam Kapsamlı Analiz

Artık sistem sadece teknik göstergelere değil, **beş bağımsız analiz
katmanına** bakıyor:

| Katman | Ne ölçer | Kripto'da geçerli mi |
|---|---|---|
| Teknik (ADX/EMA/RSI/MACD) | Trend/rejim, momentum, risk/ödül | ✅ |
| Temel analiz | F/K, PEG, ROE, borç/özkaynak, büyüme, kâr marjı | ❌ (kavram yok) |
| Göreceli güç | Kendi piyasa endeksine (SPY/XU100/BTC) karşı performans | ✅ |
| Hacim + haftalık teyit | Bağıl hacim, OBV yönü, haftalık trend uyumu | ✅ |
| Risk metrikleri | Yıllık volatilite, maks. düşüş, 52 haftalık aralık, beta | ✅ |

Bir sembolde bir katman eksikse (örn. kriptoda temel analiz), skorlama
motoru o bileşeni **otomatik olarak dışarıda bırakıp kalan ağırlıkları
yeniden normalize eder** — kripto, olmayan bir veri yüzünden haksız
şekilde düşük puan almaz.

```
1. Evren yönetimi      → universe.py, data/universe_*.csv
2. Veri toplama         → data_pipeline/fetcher.py, cache.py (fiyat + benchmark)
3. Veri doğrulama       → data_pipeline/validator.py
4. Teknik analiz        → analysis/strategy.py, indicators.py
5. Temel analiz         → analysis/fundamentals.py
6. Göreceli güç         → analysis/relative_strength.py
7. Hacim/haftalık teyit → analysis/confirmations.py
8. Risk metrikleri      → analysis/risk_metrics.py
9. Skorlama (v2)        → analysis/scorer.py — tüm katmanları dinamik ağırlıklandırır
10. Filtreleme          → analysis/filters.py — kullanıcı kriterlerine göre süzer
11. Rapor oluşturma     → reporting/excel_report.py — 9 sayfalı Excel
12. Zamanlama           → scheduler.py, main_scan.py
```

## Filtreleme

`config.py > FILTERS` içinde varsayılanlar tanımlı; CLI'dan override edilebilir:

```bash
python main_scan.py --markets us bist crypto --min-score 0.3 --only-buy
python main_scan.py --markets us --max-pe 40 --min-market-cap 5000000000
python main_scan.py --markets us --skip-fundamentals   # hızlı, sadece teknik+göreceli güç
```

Filtreler eksik veriyi (örn. kriptoda P/E yok) cezalandırmaz — sadece o
kriter için değerlendirmeye almaz, sembolü otomatik elemez.



## Kurulum (kendi bilgisayarında)

```bash
cd trading_system
pip install -r requirements.txt
```

## İlk çalıştırma öncesi: gerçek listeleri çek

Depoda gelen `data/universe_*.csv` dosyaları KÜÇÜK ÖRNEK listelerdir
(40 ABD + 30 BIST + 15 kripto = 85 sembol) — bu sandbox'ın interneti
kısıtlı olduğu için tam liste çekilemedi. Kendi bilgisayarında gerçek,
güncel listeleri çekmek için:

```bash
python fetch_universe_lists.py --markets us crypto
```

Bu, S&P 500 + Nasdaq-100'ü Wikipedia'dan, ilk 50 kripto parayı
CoinGecko'dan çeker ve `data/universe_us.csv` / `universe_crypto.csv`
dosyalarını günceller. BIST için otomatik kaynak yok; `data/universe_bist.csv`
dosyasını elle güncellemen gerekir (script çalıştığında talimat basar).

## Çalıştırma

```bash
# Tüm piyasaları tara, Excel raporu oluştur
python main_scan.py --markets us bist crypto

# Sadece ABD, cache kullanmadan (taze veri zorla)
python main_scan.py --markets us --no-cache
```

Çıktı: `reports/tarama_YYYYMMDD_HHMMSS.xlsx` — sayfalar: Özet (en iyi
20 al/sat adayı), ABD, BIST, Kripto, Hata Raporu.

## Gün içi otomatik çalıştırma

İki yöntem, `scheduler.py` içinde detaylı anlatılıyor:

1. **Basit**: `python scheduler.py` çalıştır, terminali açık bırak.
   `config.py` içindeki `SCAN_TIMES_TR` listesinde tanımlı saatlerde
   (varsayılan 10:30, 13:00, 16:00, 19:00) otomatik tarar.
2. **Önerilen**: İşletim sistemi zamanlayıcısı (cron / Windows Task
   Scheduler) — bilgisayar arka planda çalışırken de güvenilir çalışır.
   Örnek cron satırı `scheduler.py` içinde.

## Test etme

```bash
python -m pytest tests/ -v          # 72 birim/entegrasyon testi
python verify_full_system.py        # Uçtan uca doğrulama (sentetik veri + kasıtlı bozuk veri)
```

Excel raporu artık 9 sayfa içerir: Özet, Filtrelenmiş, ABD, BIST, Kripto,
Temel Analiz, Risk Metrikleri, Filtre Özeti, Hata Raporu.

`verify_full_system.py` gerçekçi bir stres testidir: bazı sembollerin
verisini kasıtlı olarak bozar (eksik kolon, yetersiz satır) ve sistemin
çökmeden, doğru hata raporlayarak devam ettiğini doğrular.

## ÖNEMLİ — Bu sandbox'ta neden gerçek veriyle test edilmedi

Bu ortamın ağ erişimi Yahoo Finance ve CoinGecko'ya kapalı. Bu yüzden
tüm doğrulama sentetik (rastgele üretilmiş) veriyle yapıldı — kodun
MANTIĞININ doğru çalıştığını kanıtlar, ama gerçek piyasa performansı
hakkında hiçbir şey söylemez. Kendi bilgisayarında gerçek verilerle
çalıştırdığında sonuçlar tamamen farklı olacaktır.

## Skorlama mantığı (özet)

Farklı piyasalar (BIST hissesi, ABD hissesi, kripto) doğrudan
karşılaştırılamaz — farklı volatilite rejimleri, farklı birimler.
`analysis/scorer.py` her sembolü şu bileşenlerle -1 ile +1 arasında
tek bir skora indirger:
- **Sinyal gücü** (%35): ADX'in eşik üstündeki gücü / RSI'ın aşırı bölgeden uzaklığı
- **Momentum** (%25): son 20 günlük getiri
- **Risk/ödül** (%25): ATR tabanlı hedef/stop mesafesi oranı
- **Volatilite cezası** (%15): aşırı oynaklık skoru düşürür

Ağırlıklar `config.py > SCORE_WEIGHTS` içinden değiştirilebilir.

## Bilinen sınırlamalar ve dürüst uyarılar

1. **"Kusursuz sistem" yoktur.** Bu sistem sağlam mühendislik (test
   edilmiş, hataya dayanıklı, şeffaf) sağlar — piyasa performansı
   garantisi değil. Hiçbir backtest veya tarama sistemi bunu veremez.
2. **yfinance ücretsiz/gayri resmi bir kaynaktır.** Büyük evrenlerde
   (yüzlerce-binlerce sembol) sık çekim yapmak IP kısıtlamasına yol
   açabilir. Cache + batch + delay bunu azaltır ama sıfırlamaz.
   Ölçek büyüdükçe ücretli bir sağlayıcıya (Polygon.io, Finnhub,
   Alpaca Data) geçmeyi düşün.
3. **Parametreler optimize edilmedi.** ADX eşiği, RSI seviyeleri, ATR
   çarpanları makul varsayılan değerlerdir. Gerçek kullanım için
   walk-forward / out-of-sample optimizasyon şart — yoksa overfitting
   (veriye ezberleme) riski var.
6. **Temel analiz çekimi yavaştır.** yfinance'in `.info` çağrısı sembol
   başına ayrı bir HTTP isteğidir. Büyük evrenlerde (yüzlerce sembol)
   tam tarama birkaç dakika sürebilir. Hızlı sonuç istiyorsan
   `--skip-fundamentals` kullan.
7. **Beta/göreceli güç hesapları benchmark verisinin doğruluğuna bağlı.**
   `XU100.IS` gibi endeks sembolleri yfinance'te bazen tutarsız veri
   verebilir; sonuç şüpheli görünüyorsa `analysis/relative_strength.py`
   içindeki `BENCHMARKS` sözlüğünü kontrol et.
4. **BIST intraday veri sınırlıdır.** yfinance BIST için çoğunlukla
   günlük veri sağlar; "gün içi birkaç kez tarama" pratikte günlük
   veriyi birkaç kez yeniden değerlendirmek anlamına gelir, her taramada
   yeni mum oluşmaz. Gerçek gün içi (intraday) analiz için BIST'e özel
   ücretli bir veri kaynağı gerekir.
5. **Bu bir yatırım tavsiyesi değildir.** Üretilen AL/SAT sinyalleri
   kural tabanlı bir modelin çıktısıdır, finansal tavsiye değildir.
   Kararların sorumluluğu sana aittir; gerekirse bir yatırım
   danışmanına başvur.
8. **"Tüm borsa sembolleri" değil, "en önemli 100 + 100 + 100 + altın".**
   Binlerce/on binlerce sembole (dünyadaki tüm hisseler, tüm kripto
   paralar) erişim ücretli kurumsal veri sağlayıcı gerektirir. Bu sistem
   bilinçli olarak ABD'nin en büyük 100 şirketi + BIST 100 + piyasa
   değerine göre ilk 100 kripto + altına odaklanıyor — bu, "her şeyi
   yüzeysel taramak" yerine "önemli olanı derinlemesine taramak" tercihi.
9. **Haber "analizi" basit anahtar kelime sayımıdır, gerçek NLP değil.**
   Detaylar için yukarıdaki "v4 — Haber analizi" bölümüne bakın.

## 🆕 v7 — Görsel Panel: Grafikler, KPI Kartları, Sekmeli Detaylı Tasarım

Streamlit arayüzü, ham tablolardan gerçek bir görsel panele dönüştürüldü:

- `reporting/dashboard_charts.py` — Plotly ile üretilen, Streamlit'ten
  BAĞIMSIZ, pytest ile test edilen saf grafik fonksiyonları (16 test).
  Bu ayrım bilinçli: grafik mantığı tarayıcı açmadan doğrulanabiliyor.
- Mum grafiği için veri kaynağı: `data_pipeline/cache.py`'nin zaten
  diskte tuttuğu (parquet) fiyat verisi — ekstra bir indirme gerekmiyor,
  bir önceki taramanın verisi tekrar kullanılıyor.
- 9 sekme: Genel Bakış, Grafik İnceleme, Piyasalar, Temel & Risk &
  Gelişmiş, Grid & DCA, Haberler, Ekonomik Takvim, Geçmiş Performans,
  Hata Raporu.

**Doğrulama notu:** Streamlit'in kendisi interaktif olduğu için otomatik
testler tarayıcı etkileşimini simüle edemiyor — bunun yerine app.py'nin
tarama-sonrası TÜM veri işleme mantığı (Excel okuma, liste ayrıştırma,
cache erişimi, grafik üretimi), gerçek bir rapor üzerinde Streamlit'siz
ayrıca çalıştırılıp doğrulandı (40 sembol, tüm sekmeler, sıfır hata).

## 🆕 v6 — Grid ve DCA Strateji Planları

Bu, [OctoBot](https://github.com/Drakkar-Software/OctoBot) (Fransız açık
kaynaklı kripto trading botu) incelenirken ortaya çıkan bir istek üzerine
eklendi. **OctoBot'un kodu kopyalanmadı** (GPL-3.0 lisanslı olduğu için
kopyalamak bizim projeyi de GPL yapardı) — Grid ve DCA zaten genel,
herkese açık trading kavramları olduğu için kendi mantığımızla,
sıfırdan yazıldı.

**En önemli fark:** OctoBot gerçek borsa hesabına bağlanıp otomatik emir
gönderiyor. Bu sistem HİÇBİR ZAMAN gerçek emir göndermez — sadece bir
plan/öneri üretir, sen ister elle uygularsın, ister borsanın kendi
Grid Bot özelliğine bu seviyeleri girersin.

### Grid planı

Sadece **yatay (range) rejimindeki** semboller için anlamlıdır (trend
halindeki sembollerde fiyat tek yöne kaçabileceği için grid stratejisi
önerilmez). Son 60 günlük fiyat aralığı N eşit dilime bölünür, her dilim
için bir AL fiyatı + bir SAT fiyatı (bir dilim üstü) hesaplanır.
"Grid Planı" sayfasında.

### DCA (kademeli alım) planı

AL sinyali üreten semboller için, tek seferde büyük pozisyon açmak
yerine bütçeyi 4 dilime bölüp fiyat düştükçe kademeli alım önerir
(varsayılan: her dilim %5 daha düşük fiyatta tetiklenir). "DCA Planı"
sayfasında.

**Dürüstlük notu:** Fiyat öngörülen seviyelere hiç gelmeyebilir — bu
DCA'nın doğasında var, "bazı dilimler hiç alınmadı" normal bir sonuçtur,
hata değildir.



### Altın veri sorunu neden yaşandı, nasıl çözüldü

`GC=F` (COMEX altın vadeli işlemi) bir vadeli işlem sözleşmesiydi — bu tür
sözleşmeler rollover (sözleşme devri) dönemlerinde ve Yahoo Finance'in
emtia veri hattında hisse senetlerine göre daha sık boşluk/eksiklik
yaşıyor. Sembol artık `XAUUSD=X` (spot altın/dolar, forex-tarzı sürekli
kota) — çok daha kararlı bir veri akışı sağlıyor.

### İkinci, bağımsız veri kaynağı: Stooq.com

`data_pipeline/stooq_fetcher.py`, tamamen ücretsiz ve API key
gerektirmeyen Stooq.com'u iki şekilde kullanır:

1. **Yedek kaynak**: yfinance bir sembol için tüm denemelerinde
   başarısız olursa (rate limit, geçici sunucu sorunu), sistem otomatik
   olarak Stooq'u dener. ABD hisseleri, kripto paralar ve altın için
   çalışır; BIST için Stooq güvenilir kapsam sağlamadığından uygulanmaz.
2. **Çapraz doğrulama**: Sinyal üreten her sembol için hem yfinance hem
   Stooq'tan son kapanış fiyatı karşılaştırılır. İki kaynak %3'ten fazla
   farklıysa, Excel raporunda "Veri Şüpheli mi" sütunu işaretlenir —
   kör güven yerine iki bağımsız kaynağın birbirini denetlemesi.

Atlamak istersen: `python main_scan.py --skip-cross-validation`

### Mum formasyonu (candlestick pattern) tanıma

`analysis/candlestick_patterns.py`, klasik formasyonları (doji, çekiç,
kayan yıldız, boğa/ayı yutan formasyonu) OHLC verisinden tespit eder,
"Gelişmiş Göstergeler" sayfasına ek sütun olarak eklenir.

**Dürüstlük notu:** Mum formasyonları tek başına güvenilir bir sinyal
değildir — akademik literatür karışık sonuçlar veriyor. Trend/rejim ve
diğer göstergelerle BİRLİKTE bir teyit katmanı olarak kullanın.

### Pozisyon büyüklüğü önerisi

`analysis/position_sizing.py`, bir sinyali "kaç hisse/kripto/lot al"a
çevirir — ATR tabanlı stop mesafesine göre, hesabının sabit bir yüzdesini
(varsayılan %1) riske atacak şekilde boyutlandırma yapar. Bu, "sinyal
listesi" ile "gerçek bir trade sistemi" arasındaki en önemli farklardan
biridir.

```bash
python main_scan.py --account-size 50000 --risk-pct 1.5
```

Streamlit arayüzünde de "Pozisyon Büyüklüğü" bölümünden ayarlanabilir.

**Dürüstlük notu:** Bu bir öneri motorudur, kesin talimat değil. Aynı
anda birden fazla sinyal takip ediyorsan, pozisyonlar arası korelasyona
(örn. aynı sektörden 5 hisse aynı anda AL sinyali verirse bunlar
bağımsız riskler değildir) dikkat etmen gerekir — sistem şu an
portföy-seviyesi korelasyon kontrolü yapmıyor.

### Ekonomik takvim

`analysis/economic_calendar.py`, önümüzdeki 14 gün içinde FOMC (Fed
faiz kararı), NFP (istihdam) veya CPI (enflasyon) açıklaması var mı
kontrol eder — "Ekonomik Takvim" sayfasında görünür. Az önce sorduğun
"ABD'deki açıklamalar önemli oluyor" konusuna doğrudan cevap.

**Dürüstlük notu:** FOMC tarihleri Fed'in resmi 2026 takviminden alındı
ama yılda bir elle güncellenmesi gerekir. NFP/CPI tarihleri **yaklaşık**
kurallara dayanır (kesin gün için bls.gov'un resmi takvimine bakılmalı).



### Neden "top 100" mantığı?

BIST 100 gibi, artık ABD ve kripto piyasaları da "en önemli/en büyük 100"
mantığıyla taranıyor — dağınık, kalitesiz sembollerle vakit kaybetmek
yerine, gerçekten önemli olan hisselere odaklanıyoruz:

| Piyasa | Kaynak | Kapsam |
|---|---|---|
| ABD | S&P 100 (Wikipedia, canlı çekim) | En büyük/en likit 100 ABD şirketi |
| BIST | Elle derlenmiş, investing.com'un 30.08.2026 tarihli BIST 100 sayfasından | 80 doğrulanmış sembol (bkz. aşağıdaki dürüstlük notu) |
| Kripto | CoinGecko (canlı çekim) | Piyasa değerine göre ilk 100 |
| Altın | Statik | COMEX Altın Vadeli İşlemi (`GC=F`) |

Daha geniş ABD kapsamı istersen: `python fetch_universe_lists.py --markets us --us-extended`
(S&P 500 + Nasdaq-100 ekler, ama tarama süresi uzar).

### BIST 100 listesi hakkında dürüstlük notu

80 sembollük liste, investing.com'un canlı BIST 100 bileşen sayfasından
şirket adı okunup ticker koduna **elle eşlenerek** oluşturuldu (BIST için
güvenilir, ücretsiz, makine tarafından okunabilir bir kaynak yok). Bazı
küçük/yeni halka arz olmuş şirketlerin ticker kodları belirsizliği
nedeniyle listeye dahil edilmedi. Yanlış bir kod varsa, sistem bunu
otomatik olarak "Hata Raporu" sayfasına düşürür, çökmez — ama %100
doğruluk garantisi veremem. Endeks çeyreklik revize edildiği için
(Ocak/Nisan/Temmuz/Ekim) listeyi periyodik olarak elle güncellemen
gerekir. Güncel resmi liste: tr.investing.com/indices/ise-100-components

### Altın analizi

Diğer piyasalarla aynı teknik analiz motorundan geçer (rejim tespiti,
Fibonacci, destek/direnç, hacim profili). Farkı: temel analiz (P/E vb.)
uygulanmaz (kripto gibi, çünkü kavram yok) ve göreceli güç karşılaştırması
yapılmaz (doğal bir "altın piyasası endeksi" yok).

### Haber analizi

Her taranan sembol için son haber başlıkları + basit bir "haber tonu"
skoru, ayrıca ABD piyasasını genel etkileyen büyük göstergelerin (S&P 500,
Dow, Nasdaq, 10 yıllık tahvil getirisi, dolar endeksi) haberleri —
Fed açıklamaları, enflasyon verileri gibi "piyasayı geneli sarsan" haberler
genelde bu göstergelerin haber akışında da görünür.

**ÖNEMLİ DÜRÜSTLÜK NOTU:** Bu, yapay zeka destekli gerçek bir haber
analizi DEĞİLDİR. Basit bir anahtar kelime sayımı yapıyor ("surge",
"plunge", "beat", "miss" gibi kelimelerin metinde geçme sıklığına
bakıyor). Bunun sebebi ücretsiz kalmak — gerçek NLP/LLM tabanlı analiz
ücretli bir API gerektirir. Haber tonu skorunu **kaba bir gösterge**
olarak kullan, kesin bir yargı olarak değil. Excel'deki "Haberler"
sayfasından başlıkları okuyup kendi değerlendirmeni yapman en sağlıklısı.

Hızlı taramak istersen: `python main_scan.py --skip-news` (sembol başına
ayrı istek gerektirdiği için yavaşlatabilir, tıpkı `--skip-fundamentals` gibi).



### Gelişmiş teknik göstergeler

`analysis/advanced_indicators.py` her sembol için ek olarak hesaplar:
- **Fibonacci seviyeleri**: Son önemli yükseliş/düşüşe göre %23.6, %38.2,
  %50, %61.8, %78.6 geri çekilme seviyeleri, ve fiyata en yakın seviye
- **Destek/direnç**: Yerel dip/zirve noktalarından (pivot) türetilen,
  birbirine yakın olanları kümeleyen seviye listesi
- **Hacim profili**: Fiyat aralıklarına göre işlem hacmi dağılımı; POC
  (en çok işlem gören fiyat) ve "value area" (hacmin %70'inin gerçekleştiği
  aralık)

Excel raporunda **"Gelişmiş Göstergeler"** sayfasında görünür.

### Sinyal günlüğü / performans takibi

`analysis/journal.py`, her taramada üretilen sinyalleri `data/signal_journal.db`
adlı bir SQLite veritabanına kaydeder ve bir sonraki taramada:
- Daha önce açılan sinyallerin hedefe mi ulaştığını, stop mu olduğunu,
  hâlâ açık mı olduğunu günceller
- 30 günden eski hâlâ açık sinyalleri "süresi doldu" olarak işaretler
- Kazanma oranı, ortalama getiri gibi özet istatistikler üretir

Excel raporunda **"Performans Geçmişi"** sayfasında görünür. Bu, sistemin
gerçekten işe yarayıp yaramadığını zamanla objektif olarak görmeni sağlar
— tek seferlik bir tarama değil, kendini denetleyen bir döngü.

Veritabanı dosyasını silersen geçmiş sıfırlanır; normalde silme, zamanla
biriken veri değerlidir.

### Sembol listelerinin otomatik güncellenmesi

Artık `fetch_universe_lists.py`'yi elle çalıştırman gerekmiyor. Her
taramadan önce `universe.auto_refresh_if_stale()` şunu kontrol eder:
`data/universe_us.csv` ve `data/universe_crypto.csv` dosyaları
`config.py > UNIVERSE_MAX_AGE_DAYS` (varsayılan 7 gün) değerinden eskiyse,
otomatik olarak yeniden çeker. İnternet yoksa veya çekim başarısız olursa
mevcut (eski) listeyle devam eder, sistemi durdurmaz.

Kapatmak istersen: `python main_scan.py --no-auto-refresh`

### Telegram bildirimleri

Her tarama bitince, en iyi AL/SAT adaylarını Telegram'a mesaj olarak
gönderebilir. Kurulum (tek seferlik, ücretsiz):

1. Telegram'da **@BotFather** hesabını bul, `/newbot` yaz, talimatları
   takip et (bot adı sor, istediğini yaz). Sonunda sana uzun bir
   **TOKEN** verir (örn. `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`) — kopyala.
2. Oluşturduğun botu Telegram'da ara, konuşmayı başlat, herhangi bir
   mesaj gönder (örn. "merhaba").
3. Tarayıcında şu adrese git (TOKEN kısmını kendi tokenınla değiştir):
   `https://api.telegram.org/bot TOKEN /getUpdates` (boşluksuz yaz)
4. Çıkan metinde `"chat":{"id":123456789,...}` gibi bir kısım ara,
   oradaki sayı senin **CHAT_ID**'n.
5. Bilgisayarında ortam değişkeni olarak ayarla:

   **Windows (PowerShell'de, kalıcı olması için):**
   ```
   setx TELEGRAM_BOT_TOKEN "buraya_token"
   setx TELEGRAM_CHAT_ID "buraya_chat_id"
   ```
   Ayarladıktan sonra **terminali kapatıp yeniden aç** (yeni pencere
   değişkeni görmeli).

   **Mac/Linux:**
   ```
   echo 'export TELEGRAM_BOT_TOKEN="buraya_token"' >> ~/.zshrc
   echo 'export TELEGRAM_CHAT_ID="buraya_chat_id"' >> ~/.zshrc
   source ~/.zshrc
   ```

Bundan sonra her tarama bitince Telegram'a otomatik mesaj gelir. Hiç
ayarlamazsan sistem bunu fark eder, sessizce atlar — hata vermez.

---

## ☁️ Bulutta Ücretsiz 7/24 Çalıştırma (bilgisayarın kapalıyken de)

Bu, **GitHub Actions** kullanır — GitHub'ın herkese açık projeler için
tamamen ücretsiz sunduğu bir otomasyon hizmeti. Kredi kartı gerekmez.
Proje zaten `.github/workflows/scan.yml` dosyasıyla hazır; sadece
GitHub'a yüklemen ve birkaç ayar yapman yeterli.

### 1. GitHub hesabı aç

[github.com](https://github.com) → "Sign up" → ücretsiz hesap oluştur.

### 2. Yeni bir "repository" (depo) oluştur

- Sağ üstteki **+** işaretine tıkla → **"New repository"**
- İsim ver (örn. `hisse-tarama-sistemi`)
- **"Private"** seçeneğini işaretle (sinyal geçmişin ve ayarların
  herkese açık olmasın istersen — ücretsiz hesapta private repo da
  Actions'ı ücretsiz kullanabilir)
- "Create repository" butonuna bas

### 3. Proje dosyalarını yükle

Oluşan boş depo sayfasında **"uploading an existing file"** linkine
tıkla. Bilgisayarındaki `trading_system` klasörünün **içindeki tüm
dosya ve klasörleri** (klasörün kendisini değil, içindekileri) sürükleyip
bırak. Yüklenmesi biraz sürebilir (yüzlerce dosya var). Sonunda
"Commit changes" butonuna bas.

**Not:** `venv` klasörünü YÜKLEME (gereksiz, çok büyük). `cache`,
`logs`, `__pycache__`, `.pytest_cache` klasörlerini de yüklemene
gerek yok.

### 4. Telegram bilgilerini "Secret" olarak ekle (bildirim istiyorsan)

- Depo sayfasında **Settings** (Ayarlar) sekmesine git
- Sol menüden **Secrets and variables → Actions**
- **"New repository secret"** butonuna bas
- İsim: `TELEGRAM_BOT_TOKEN`, Değer: kendi token'ın → "Add secret"
- Aynısını `TELEGRAM_CHAT_ID` için de tekrarla

### 5. Yazma iznini aç (rapor otomatik kaydedilsin diye)

- **Settings → Actions → General** sayfasına git
- En altta **"Workflow permissions"** bölümünü bul
- **"Read and write permissions"** seçeneğini işaretle → Save

### 6. Çalıştığını doğrula

- Depo sayfasında **Actions** sekmesine git
- Soldan **"Otomatik Hisse/Kripto Taraması"** iş akışına tıkla
- Sağda **"Run workflow"** butonuna basıp elle bir kere tetikle
- Birkaç dakika sonra yeşil tik ✅ görürsen çalışıyor demektir
- Tıklayıp içine girersen adım adım logları görebilirsin (tıpkı kendi
  terminalinde gördüğün gibi)

Bundan sonra **hafta içi günde 4 kez** (10:30, 13:00, 16:00, 19:00
Türkiye saati) otomatik çalışır, sonuçları hem depoya kaydeder hem
(ayarladıysan) Telegram'a gönderir — bilgisayarın kapalı olsa bile.

**Saatleri değiştirmek istersen:** `.github/workflows/scan.yml`
dosyasındaki `cron` satırlarını düzenle (UTC saatiyle yazılır, Türkiye
saatinden 3 saat geridir).

**Ücretsiz sınırı:** Private repo'larda ayda ~2000 dakika (bu tarama
sıklığıyla fazlasıyla yeterli); public repo'larda sınırsız.

## Sonraki adımlar (istersen genişletebiliriz)

- ~~Fundamental veri entegrasyonu~~ ✅ tamamlandı
- ~~Gelişmiş teknik göstergeler (Fibonacci, destek/direnç, hacim profili)~~ ✅ tamamlandı
- ~~Sinyal günlüğü / performans takibi~~ ✅ tamamlandı
- ~~Telegram bildirimleri~~ ✅ tamamlandı
- ~~Bulutta ücretsiz otomatik çalıştırma~~ ✅ tamamlandı
- ~~Genişletilmiş sembol kapsamı (S&P 100, BIST 100, kripto top 100, altın)~~ ✅ tamamlandı
- ~~Haber analizi (sembol bazlı + makro)~~ ✅ tamamlandı (basit anahtar kelime tabanlı, gerçek NLP değil)
- ~~İkinci/bağımsız veri kaynağı (Stooq) + çapraz doğrulama~~ ✅ tamamlandı
- ~~Mum formasyonu tanıma~~ ✅ tamamlandı
- ~~Pozisyon büyüklüğü önerisi~~ ✅ tamamlandı
- ~~Ekonomik takvim (FOMC/NFP/CPI)~~ ✅ tamamlandı
- ~~Grid ve DCA strateji planları~~ ✅ tamamlandı
- ~~Görsel panel: grafikler, KPI kartları, sekmeli detaylı tasarım~~ ✅ tamamlandı
- Walk-forward parametre optimizasyonu scripti (parametreler hâlâ optimize edilmedi — bkz. "Bilinen sınırlamalar")
- Paper trading (kağıt üzerinde) takip modülü — journal.py bunun temelini atıyor ama gerçek zamanlı simülasyon değil
- E-posta bildirimi (şu an sadece Telegram var)
- Gerçek NLP/LLM tabanlı haber duygu analizi (ücretli API gerektirir)
- Portföy-seviyesi korelasyon kontrolü (birden fazla sinyal arasındaki bağımlılık analizi)
- Ichimoku Cloud, Stochastic osilatör gibi ek teknik göstergeler

