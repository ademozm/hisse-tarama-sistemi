"""
Bu sandbox'ta gerçek Yahoo Finance/CoinGecko erişimi yok. Bu script,
TÜM sistemi (evren -> fiyat verisi -> doğrulama -> teknik analiz ->
gelişmiş göstergeler -> temel analiz -> göreceli güç -> hacim/haftalık
teyit -> risk metrikleri -> skorlama -> filtreleme -> sinyal günlüğü
-> Excel raporu -> bildirim) sentetik veriyle uçtan uca doğrular.
Gerçek bilgisayarında main_scan.py gerçek veriyle aynı şekilde çalışacaktır.
"""
import os
import numpy as np
import pandas as pd

import universe
from data_pipeline import validator
from analysis.strategy import RegimeAdaptiveStrategy
from analysis import (
    scorer, fundamentals, relative_strength, confirmations, risk_metrics,
    filters, advanced_indicators, journal, notifier,
)
from reporting import excel_report


def make_synthetic(symbol, n=300, seed=None):
    seed = seed if seed is not None else abs(hash(symbol)) % (2**32)
    rng = np.random.default_rng(seed)
    n_blocks = 6
    returns = []
    while len(returns) < n:
        drift = rng.choice([0.003, -0.003, 0.0])
        vol = rng.uniform(0.01, 0.03)
        block_len = n // n_blocks
        returns.extend(rng.normal(drift, vol, block_len))
    returns = np.array(returns[:n])
    close = 100 * np.exp(np.cumsum(returns))
    dates = pd.date_range(end=pd.Timestamp.now().normalize(), periods=n, freq="D")
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    df = pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close,
                        "Volume": rng.integers(1000, 100000, n)}, index=dates)
    df["High"] = df[["Open", "High", "Low", "Close"]].max(axis=1)
    df["Low"] = df[["Open", "High", "Low", "Close"]].min(axis=1)
    return df


def make_synthetic_fundamentals(symbol, market, seed=None):
    if market == "crypto":
        return {}
    seed = seed if seed is not None else abs(hash(symbol)) % (2**32)
    rng = np.random.default_rng(seed)
    return {
        "trailingPE": float(rng.uniform(5, 100)), "forwardPE": float(rng.uniform(5, 90)),
        "priceToBook": float(rng.uniform(0.5, 15)), "pegRatio": float(rng.uniform(0.3, 5)),
        "returnOnEquity": float(rng.uniform(-0.2, 0.4)), "debtToEquity": float(rng.uniform(0, 300)),
        "revenueGrowth": float(rng.uniform(-0.2, 0.4)), "earningsGrowth": float(rng.uniform(-0.3, 0.5)),
        "dividendYield": float(rng.uniform(0, 0.05)), "marketCap": float(rng.uniform(1e8, 2e12)),
        "profitMargins": float(rng.uniform(-0.1, 0.35)),
    }


print("[ 1/11] Evren yükleniyor (tüm piyasalar)...")
universe_df = universe.load_universe()
print(f"        Toplam {len(universe_df)} sembol")

print("[ 2/11] Sentetik fiyat verisi + benchmark üretiliyor...")
raw_data = {sym: make_synthetic(sym) for sym in universe_df["symbol"]}
raw_data[universe_df["symbol"].iloc[0]] = pd.DataFrame({"Close": [1, 2, 3]})
raw_data[universe_df["symbol"].iloc[1]] = make_synthetic("SHORT", n=10)
benchmark_data = {
    "us": make_synthetic("SPY", seed=999), "bist": make_synthetic("XU100.IS", seed=998),
    "crypto": make_synthetic("BTC-USD", seed=997),
}

print("[ 3/11] Doğrulama...")
valid_data, validation_report = validator.validate_batch(raw_data)
print(f"        Geçerli: {len(valid_data)} / {len(raw_data)}")

print("[ 4/11] Teknik sinyal üretimi...")
strat = RegimeAdaptiveStrategy()
signals = {}
for sym, df in valid_data.items():
    try:
        signals[sym] = strat.generate_signals(df)
    except Exception as e:
        print(f"        UYARI: {sym} sinyal üretiminde hata: {e}")

print("[ 5/11] Gelişmiş göstergeler (Fibonacci, destek/direnç, hacim profili)...")
advanced_by_symbol = {}
for sym, sig_df in signals.items():
    advanced_by_symbol[sym] = advanced_indicators.compute_all(sig_df)
print(f"        {len(advanced_by_symbol)} sembol için hesaplandı")

print("[ 6/11] Sentetik temel analiz verisi üretiliyor ve skorlanıyor...")
market_by_symbol = universe_df.set_index("symbol")["market"].to_dict()
raw_fundamentals = {sym: make_synthetic_fundamentals(sym, market_by_symbol.get(sym, "us")) for sym in signals}
fundamentals_df = fundamentals.compute_fundamental_scores(raw_fundamentals)

print("[ 7/11] Göreceli güç hesaplanıyor...")
rs_df = relative_strength.compute_relative_strength_batch(valid_data, universe_df, benchmark_data)

print("[ 8/11] Hacim/haftalık teyit + risk metrikleri hesaplanıyor...")
confirmations_by_symbol, risk_by_symbol = {}, {}
for sym, sig_df in signals.items():
    last_signal = int(sig_df.iloc[-1]["signal"])
    confirmations_by_symbol[sym] = confirmations.compute_confirmations(sig_df, last_signal)
    bench = benchmark_data.get(market_by_symbol.get(sym))
    risk_by_symbol[sym] = risk_metrics.compute_all(sig_df, bench["Close"] if bench is not None else None)

print("[ 9/11] Skorlama ve filtreleme...")
scored_df = scorer.score_universe(
    signals, universe_df, fundamentals_df=fundamentals_df, relative_strength_df=rs_df,
    confirmations_by_symbol=confirmations_by_symbol, risk_metrics_by_symbol=risk_by_symbol,
)
if not scored_df.empty and advanced_by_symbol:
    adv_df = pd.DataFrame([{"symbol": s, **a} for s, a in advanced_by_symbol.items()])
    scored_df = scored_df.merge(adv_df, on="symbol", how="left")
print(f"        Sinyal üreten sembol sayısı: {len(scored_df)}")
if not scored_df.empty:
    assert not scored_df["composite_score"].isna().any(), "composite_score içinde NaN olmamalı!"

import config
filtered_df, filter_stats = filters.apply_filters(scored_df, config.FILTERS)
print(f"        Filtre öncesi: {filter_stats.get('başlangıç', 0)}, filtre sonrası: {filter_stats.get('son', 0)}")

print("[10/11] Sinyal günlüğü test ediliyor (SQLite)...")
test_db_path = "/home/claude/trading_system/data/test_verify_journal.db"
if os.path.exists(test_db_path):
    os.remove(test_db_path)
journal.update_outcomes(valid_data, db_path=test_db_path)  # boş DB'de no-op olmalı
added = journal.record_signals(scored_df, pd.Timestamp.now().isoformat(), db_path=test_db_path)
print(f"        {added} sinyal günlüğe kaydedildi")
outcome_stats = journal.update_outcomes(valid_data, db_path=test_db_path)
print(f"        Sonuç güncellemesi: {outcome_stats}")
performance_df = journal.compute_performance_stats(db_path=test_db_path)
print(f"        Performans tablosu: {len(performance_df)} satır")
os.remove(test_db_path)

print("[11/11] Excel raporu + bildirim test ediliyor...")
output_path = "/home/claude/trading_system/reports/dogrulama_raporu.xlsx"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
excel_report.build_report(scored_df, validation_report, output_path,
                           filtered_df=filtered_df, filter_stats=filter_stats,
                           performance_stats_df=performance_df)

# Telegram yapılandırılmamış olduğu için False dönmeli, hata FIRLATMAMALI
notified = notifier.notify_scan_complete(filtered_df, filter_stats, output_path)
assert notified is False, "Telegram yapılandırılmamışken sessizce False dönmeli"
print("        Bildirim modülü doğru şekilde atlandı (Telegram yapılandırılmamış)")

sheets = pd.read_excel(output_path, sheet_name=None)
print(f"\nOluşan Excel sayfaları: {list(sheets.keys())}")
for name, sheet in sheets.items():
    print(f"  - {name}: {len(sheet)} satır")

expected_sheets = {"Özet", "Filtrelenmiş", "ABD", "BIST", "Kripto", "Temel Analiz",
                   "Gelişmiş Göstergeler", "Risk Metrikleri", "Performans Geçmişi",
                   "Filtre Özeti", "Hata Raporu"}
assert expected_sheets.issubset(set(sheets.keys())), f"Eksik sayfa(lar): {expected_sheets - set(sheets.keys())}"

print("\n✓ TÜM SİSTEM (v3: GELİŞMİŞ GÖSTERGELER + SİNYAL GÜNLÜĞÜ + BİLDİRİM DAHİL) UÇTAN UCA BAŞARIYLA ÇALIŞTI.")
