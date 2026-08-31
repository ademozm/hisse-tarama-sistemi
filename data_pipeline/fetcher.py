"""
Çoklu sembol veri çekme katmanı.

Tasarım kararları:
- Cache-first: TTL süresi dolmamış veri diskte varsa tekrar indirilmez.
- Batch + delay: sembolller küçük gruplar halinde, aralarda bekleyerek
  indirilir (rate-limit koruması).
- Retry + backoff: geçici ağ hatalarında birkaç kez tekrar denenir.
- Kısmi başarısızlık toleransı: bir sembol başarısız olursa tüm tarama
  durmaz, o sembol "failed" listesine eklenir ve rapora not düşülür.
"""
import time
import logging
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

import config
from data_pipeline import cache

logger = logging.getLogger("fetcher")


@dataclass
class FetchResult:
    data: dict = field(default_factory=dict)     # symbol -> DataFrame
    failed: dict = field(default_factory=dict)    # symbol -> hata mesajı
    from_cache: set = field(default_factory=set)  # cache'den gelen semboller


def _fetch_one(symbol: str, period: str, interval: str) -> pd.DataFrame:
    last_err = None
    for attempt in range(1, config.FETCH_MAX_RETRIES + 1):
        try:
            df = yf.download(
                symbol, period=period, interval=interval,
                progress=False, auto_adjust=True, threads=False,
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty:
                raise ValueError("Boş veri döndü")
            return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        except Exception as e:
            last_err = e
            logger.warning(f"{symbol} deneme {attempt}/{config.FETCH_MAX_RETRIES} başarısız: {e}")
            if attempt < config.FETCH_MAX_RETRIES:
                time.sleep(config.FETCH_RETRY_BACKOFF_SEC * attempt)
    raise RuntimeError(f"{symbol} indirilemedi: {last_err}")


def fetch_universe(
    symbols: list[str],
    period: str = None,
    interval: str = None,
    use_cache: bool = True,
) -> FetchResult:
    period = period or config.FETCH_PERIOD
    interval = interval or config.FETCH_INTERVAL
    result = FetchResult()

    to_fetch = []
    for sym in symbols:
        if use_cache:
            cached_df = cache.get_cached(sym, interval)
            if cached_df is not None:
                result.data[sym] = cached_df
                result.from_cache.add(sym)
                continue
        to_fetch.append(sym)

    logger.info(f"{len(result.from_cache)} sembol cache'den, {len(to_fetch)} sembol indirilecek.")

    for i in range(0, len(to_fetch), config.FETCH_BATCH_SIZE):
        batch = to_fetch[i:i + config.FETCH_BATCH_SIZE]
        for sym in batch:
            try:
                df = _fetch_one(sym, period, interval)
                result.data[sym] = df
                cache.set_cached(sym, interval, df)
            except Exception as e:
                result.failed[sym] = str(e)
        if i + config.FETCH_BATCH_SIZE < len(to_fetch):
            time.sleep(config.FETCH_BATCH_DELAY_SEC)

    return result
