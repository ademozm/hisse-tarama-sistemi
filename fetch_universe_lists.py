"""
Kendi bilgisayarında (bu sandbox'ta DEĞİL, çünkü buranın interneti kısıtlı)
data/universe_*.csv dosyalarını GERÇEK ve GÜNCEL listelerle doldurmak için
çalıştır:

    python fetch_universe_lists.py --markets us crypto
    python fetch_universe_lists.py --markets us bist crypto

BIST için otomatik canlı kaynak eklenmedi çünkü güvenilir/ücretsiz bir API
yok; --markets bist seçilirse elle güncellenmiş data/universe_bist.csv
kullanılır ve bir uyarı basılır. Genişletmek istersen Borsa İstanbul'un
resmi hisse listesini indirip aynı CSV formatına (symbol,market,name)
dönüştürebilirsin.

Kripto listesi CoinGecko'nun ücretsiz public API'siyle piyasa değerine göre
ilk N coin çekilir (API key gerekmez, ama dakikada istek sınırı var).
"""
import argparse
import time

import pandas as pd
import requests

import config


def update_us(top_n_extra: int = 0) -> pd.DataFrame:
    print("ABD listesi çekiliyor (S&P 500 + Nasdaq-100)...")
    sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    sp500_df = pd.DataFrame({
        "symbol": sp500["Symbol"].str.replace(".", "-", regex=False),
        "market": "us",
        "name": sp500["Security"],
    })

    try:
        nasdaq_tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        nd_df = None
        for t in nasdaq_tables:
            cols_lower = [str(c).lower() for c in t.columns]
            if "ticker" in cols_lower:
                col = t.columns[cols_lower.index("ticker")]
                name_col = t.columns[cols_lower.index("company")] if "company" in cols_lower else col
                nd_df = pd.DataFrame({"symbol": t[col], "market": "us", "name": t[name_col]})
                break
        if nd_df is not None:
            sp500_df = pd.concat([sp500_df, nd_df], ignore_index=True)
    except Exception as e:
        print(f"  [uyarı] Nasdaq-100 çekilemedi, sadece S&P 500 kullanılıyor: {e}")

    combined = sp500_df.drop_duplicates(subset="symbol").reset_index(drop=True)
    print(f"  {len(combined)} ABD sembolü bulundu.")
    return combined


def update_crypto(top_n: int = 50) -> pd.DataFrame:
    print(f"Kripto listesi çekiliyor (CoinGecko, ilk {top_n})...")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": top_n, "page": 1}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame({
        "symbol": [f"{c['symbol'].upper()}-USD" for c in data],
        "market": "crypto",
        "name": [c["name"] for c in data],
    })
    print(f"  {len(df)} kripto para bulundu.")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tam hisse/kripto listelerini güncelle")
    parser.add_argument("--markets", nargs="+", default=["us", "crypto"],
                         choices=["us", "bist", "crypto"])
    parser.add_argument("--crypto-top-n", type=int, default=50)
    args = parser.parse_args()

    if "us" in args.markets:
        df = update_us()
        df.to_csv(config.UNIVERSE_FILES["us"], index=False)
        print(f"  Kaydedildi: {config.UNIVERSE_FILES['us']}")

    if "crypto" in args.markets:
        df = update_crypto(args.crypto_top_n)
        df.to_csv(config.UNIVERSE_FILES["crypto"], index=False)
        print(f"  Kaydedildi: {config.UNIVERSE_FILES['crypto']}")

    if "bist" in args.markets:
        print("BIST için otomatik canlı kaynak yok. Mevcut "
              f"{config.UNIVERSE_FILES['bist']} dosyasını elle güncellemen gerekiyor "
              "(bkz. dosyanın başındaki not).")

    print("\nBitti. main_scan.py bir sonraki çalıştırmada güncel listeleri kullanacak.")
