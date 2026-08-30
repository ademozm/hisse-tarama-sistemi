"""
Hisse evreni yönetimi.

Bu modül, taranacak sembollerin listesini data/universe_*.csv dosyalarından
okur. Buradaki listeler ÖRNEK/BAŞLANGIÇ listeleridir — tam S&P 500, tam
BIST veya tüm kripto evrenini içermez (bu ortamın internet erişimi
kısıtlı olduğu için canlı liste çekilemedi).

Listeleri genişletmek için:
- ABD: Wikipedia "List of S&P 500 companies" tablosunu CSV'ye aktarabilirsin.
- BIST: Borsa İstanbul resmi sitesinden sembol listesi indirebilirsin
  (sembollere ".IS" son eki eklemeyi unutma, örn. THYAO.IS).
- Kripto: CoinGecko/CoinMarketCap üzerinden piyasa değerine göre ilk N coin,
  sembollere "-USD" son eki ekleyerek (örn. BTC-USD).

CSV formatı sabit: symbol,market,name
"""
import os
import logging
from datetime import datetime, timedelta

import pandas as pd

import config

logger = logging.getLogger("universe")


def load_universe(markets=None) -> pd.DataFrame:
    """
    markets: None ise tüm piyasalar. Aksi halde ör. ['us', 'bist'] gibi bir liste.
    Dönüş: symbol, market, name kolonlarına sahip birleşik DataFrame.
    """
    if markets is None:
        markets = list(config.UNIVERSE_FILES.keys())

    frames = []
    for m in markets:
        path = config.UNIVERSE_FILES.get(m)
        if path is None:
            raise ValueError(f"Bilinmeyen piyasa: {m}")
        df = pd.read_csv(path)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset="symbol").reset_index(drop=True)
    return combined


def universe_size(markets=None) -> int:
    return len(load_universe(markets))


def _file_age_days(path: str) -> float:
    if not os.path.exists(path):
        return float("inf")
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return (datetime.now() - mtime).total_seconds() / 86400


def auto_refresh_if_stale(markets: list, max_age_days: int = None) -> dict:
    """
    Her piyasa için CSV dosyasının yaşını kontrol eder; eskiyse
    fetch_universe_lists.py'deki güncelleme fonksiyonlarını çağırır.
    İnternet yoksa veya çekim başarısız olursa MEVCUT dosya korunur,
    tarama bu yüzden durmaz — sadece uyarı loglanır.

    Dönüş: {market: "güncellendi" | "güncel" | "güncellenemedi (hata)"}
    """
    max_age_days = max_age_days if max_age_days is not None else config.UNIVERSE_MAX_AGE_DAYS
    results = {}

    # Döngüsel import'u önlemek için burada import ediyoruz
    try:
        import fetch_universe_lists as ful
    except ImportError:
        for m in markets:
            results[m] = "güncellenemedi (fetch_universe_lists.py bulunamadı)"
        return results

    for m in markets:
        path = config.UNIVERSE_FILES.get(m)
        if path is None:
            continue
        age = _file_age_days(path)
        if age <= max_age_days:
            results[m] = f"güncel ({age:.1f} gün önce güncellenmiş)"
            continue

        logger.info(f"{m} sembol listesi {age:.1f} gün önce güncellenmiş, tazeleniyor...")
        try:
            if m == "us":
                df = ful.update_us()
                df.to_csv(path, index=False)
            elif m == "crypto":
                df = ful.update_crypto()
                df.to_csv(path, index=False)
            elif m == "bist":
                results[m] = "otomatik kaynak yok, elle güncellenmeli (bkz. README)"
                continue
            else:
                continue
            results[m] = "güncellendi"
            logger.info(f"{m} sembol listesi güncellendi.")
        except Exception as e:
            results[m] = f"güncellenemedi (hata: {e})"
            logger.warning(f"{m} sembol listesi güncellenemedi, eski dosya kullanılacak: {e}")

    return results
