"""
Excel rapor oluşturma v2.

Sayfalar:
- Özet          : En iyi 20 al / en iyi 20 sat adayı (filtrelenmemiş, tüm sinyaller)
- Filtrelenmiş  : config.FILTERS (veya CLI override) kriterlerinden geçen sonuçlar
- ABD, BIST, Kripto : Piyasa bazlı TAM tarama sonuçları (filtrelenmemiş)
- Temel Analiz  : Ham P/E, ROE, borç, büyüme verileri (sadece hisseler)
- Risk Metrikleri : Volatilite, max drawdown, 52 haftalık aralık, beta
- Filtre Özeti  : Kaç sembolün hangi filtrede elendiğinin dökümü
- Hata Raporu   : İndirilemeyen veya doğrulamadan geçemeyen semboller

Her sayfada: donmuş başlık satırı, otomatik filtre, skor kolonunda renk skalası.
"""
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)

DISPLAY_COLUMNS = [
    "symbol", "name", "market", "signal", "regime", "composite_score",
    "close", "momentum_return_pct", "relative_strength_pct", "risk_reward",
    "atr_pct", "adx", "rsi", "fundamental_score", "relative_volume",
    "volume_confirmed", "mtf_confirmed",
]

COLUMN_LABELS = {
    "symbol": "Sembol", "name": "Şirket/Varlık", "market": "Piyasa",
    "signal": "Sinyal", "regime": "Rejim", "composite_score": "Skor",
    "close": "Kapanış", "momentum_return_pct": "Momentum %",
    "relative_strength_pct": "Göreceli Güç %", "risk_reward": "Risk/Ödül",
    "atr_pct": "ATR %", "adx": "ADX", "rsi": "RSI",
    "fundamental_score": "Temel Skor", "relative_volume": "Bağıl Hacim",
    "volume_confirmed": "Hacim Teyidi", "mtf_confirmed": "Haftalık Teyit",
}

FUNDAMENTAL_COLUMNS = [
    "symbol", "name", "market", "trailingPE", "forwardPE", "priceToBook",
    "pegRatio", "returnOnEquity", "debtToEquity", "revenueGrowth",
    "earningsGrowth", "dividendYield", "marketCap", "profitMargins",
    "fundamental_score",
]
FUNDAMENTAL_LABELS = {
    "symbol": "Sembol", "name": "Şirket", "market": "Piyasa",
    "trailingPE": "F/K (Trailing)", "forwardPE": "F/K (Forward)",
    "priceToBook": "PD/DD", "pegRatio": "PEG", "returnOnEquity": "ROE",
    "debtToEquity": "Borç/Özkaynak", "revenueGrowth": "Gelir Büyümesi",
    "earningsGrowth": "Kâr Büyümesi", "dividendYield": "Temettü Verimi",
    "marketCap": "Piyasa Değeri", "profitMargins": "Kâr Marjı",
    "fundamental_score": "Temel Skor",
}

RISK_COLUMNS = [
    "symbol", "name", "market", "volatility_annualized_pct", "max_drawdown_pct",
    "week52_high", "week52_low", "pct_from_52w_high", "pct_from_52w_low",
    "week52_range_position", "beta",
]
RISK_LABELS = {
    "symbol": "Sembol", "name": "Şirket/Varlık", "market": "Piyasa",
    "volatility_annualized_pct": "Yıllık Volatilite %",
    "max_drawdown_pct": "Maks. Düşüş %", "week52_high": "52H Zirve",
    "week52_low": "52H Dip", "pct_from_52w_high": "Zirveden Uzaklık %",
    "pct_from_52w_low": "Dipten Uzaklık %",
    "week52_range_position": "52H Aralık Konumu (0=dip,1=zirve)", "beta": "Beta",
}

ADVANCED_COLUMNS = [
    "symbol", "name", "market", "signal", "close",
    "fib_trend_direction", "nearest_fib_level", "nearest_fib_distance_pct",
    "support_levels", "resistance_levels", "poc_price",
    "value_area_low", "value_area_high",
]
ADVANCED_LABELS = {
    "symbol": "Sembol", "name": "Şirket/Varlık", "market": "Piyasa",
    "signal": "Sinyal", "close": "Kapanış",
    "fib_trend_direction": "Fib. Trend Yönü", "nearest_fib_level": "En Yakın Fib. Seviyesi",
    "nearest_fib_distance_pct": "Fib. Seviyesine Uzaklık %",
    "support_levels": "Destek Seviyeleri", "resistance_levels": "Direnç Seviyeleri",
    "poc_price": "POC (Hacim Odağı)", "value_area_low": "Değer Alanı Alt",
    "value_area_high": "Değer Alanı Üst",
}


def _style_sheet(ws, ncols, score_col_name=None, headers=None):
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col_idx in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")

    if score_col_name and headers and score_col_name in headers:
        col_idx = headers.index(score_col_name) + 1
        col_letter = get_column_letter(col_idx)
        rule = ColorScaleRule(
            start_type="min", start_color="F08080",
            mid_type="num", mid_value=0, mid_color="FFFFFF",
            end_type="max", end_color="90EE90",
        )
        ws.conditional_formatting.add(f"{col_letter}2:{col_letter}{ws.max_row}", rule)


def _safe_str_len(value) -> int:
    if pd.isna(value):
        return 0
    return len(str(value))


def _autosize(ws, df):
    for col_idx, col_name in enumerate(df.columns, start=1):
        content_max = df[col_name].map(_safe_str_len).max()
        max_len = max(content_max if pd.notna(content_max) else 0, len(str(col_name))) + 2
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len, 40)


def _write_generic_sheet(writer, df: pd.DataFrame, sheet_name: str, columns, labels, score_col=None):
    if df.empty:
        pd.DataFrame({"Not": ["Bu sayfada gösterilecek veri bulunamadı"]}).to_excel(
            writer, sheet_name=sheet_name, index=False
        )
        return

    display_df = df[[c for c in columns if c in df.columns]].copy()
    if "signal" in display_df.columns:
        display_df["signal"] = display_df["signal"].map({1: "AL", -1: "SAT"})
    for bool_col in ("volume_confirmed", "mtf_confirmed"):
        if bool_col in display_df.columns:
            display_df[bool_col] = display_df[bool_col].map({True: "Evet", False: "Hayır"}).fillna("N/A")
    for list_col in ("support_levels", "resistance_levels"):
        if list_col in display_df.columns:
            display_df[list_col] = display_df[list_col].apply(
                lambda v: ", ".join(str(x) for x in v) if isinstance(v, list) and v else "-"
            )
    display_df = display_df.rename(columns=labels)
    display_df.to_excel(writer, sheet_name=sheet_name, index=False)

    ws = writer.sheets[sheet_name]
    score_label = labels.get(score_col) if score_col else None
    _style_sheet(ws, len(display_df.columns), score_col_name=score_label, headers=list(display_df.columns))
    _autosize(ws, display_df)


def build_report(
    scored_df: pd.DataFrame,
    validation_report: dict,
    output_path: str,
    filtered_df: pd.DataFrame | None = None,
    filter_stats: dict | None = None,
    performance_stats_df: pd.DataFrame | None = None,
):
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # --- Özet: en iyi 20 al / en iyi 20 sat (filtrelenmemiş tüm evrenden) ---
        if not scored_df.empty:
            top_buy = scored_df[scored_df["signal"] == 1].head(20)
            top_sell = scored_df[scored_df["signal"] == -1].sort_values("composite_score").head(20)
            summary = pd.concat([top_buy, top_sell])
        else:
            summary = scored_df
        _write_generic_sheet(writer, summary, "Özet", DISPLAY_COLUMNS, COLUMN_LABELS, score_col="composite_score")

        # --- Filtrelenmiş sonuçlar ---
        if filtered_df is not None:
            _write_generic_sheet(writer, filtered_df, "Filtrelenmiş", DISPLAY_COLUMNS, COLUMN_LABELS,
                                  score_col="composite_score")

        # --- Piyasa bazlı tam sonuçlar ---
        for market, label in [("us", "ABD"), ("bist", "BIST"), ("crypto", "Kripto")]:
            market_df = scored_df[scored_df["market"] == market] if not scored_df.empty else scored_df
            _write_generic_sheet(writer, market_df, label, DISPLAY_COLUMNS, COLUMN_LABELS,
                                  score_col="composite_score")

        # --- Temel analiz detayı ---
        fundamental_df = scored_df[scored_df["market"] != "crypto"] if not scored_df.empty else scored_df
        _write_generic_sheet(writer, fundamental_df, "Temel Analiz", FUNDAMENTAL_COLUMNS, FUNDAMENTAL_LABELS)

        # --- Gelişmiş göstergeler (Fibonacci, destek/direnç, hacim profili) ---
        _write_generic_sheet(writer, scored_df, "Gelişmiş Göstergeler", ADVANCED_COLUMNS, ADVANCED_LABELS)

        # --- Risk metrikleri ---
        _write_generic_sheet(writer, scored_df, "Risk Metrikleri", RISK_COLUMNS, RISK_LABELS)

        # --- Performans geçmişi (sinyal günlüğü) ---
        if performance_stats_df is not None and not performance_stats_df.empty:
            performance_stats_df.to_excel(writer, sheet_name="Performans Geçmişi", index=False)
            ws = writer.sheets["Performans Geçmişi"]
            _style_sheet(ws, len(performance_stats_df.columns))
            _autosize(ws, performance_stats_df)
        else:
            note_df = pd.DataFrame({"Not": [
                "Henüz kapanmış (kazandı/kaybetti sonuçlanmış) sinyal yok. "
                "Sistem birkaç tarama sonra bu sayfayı otomatik dolduracak."
            ]})
            note_df.to_excel(writer, sheet_name="Performans Geçmişi", index=False)

        # --- Filtre özeti ---
        if filter_stats:
            stats_df = pd.DataFrame(list(filter_stats.items()), columns=["Aşama", "Kalan Sembol Sayısı"])
            stats_df.to_excel(writer, sheet_name="Filtre Özeti", index=False)
            ws = writer.sheets["Filtre Özeti"]
            _style_sheet(ws, 2)
            _autosize(ws, stats_df)

        # --- Hata raporu ---
        error_rows = [
            {"Sembol": sym, "Neden": "; ".join(vr.reasons)}
            for sym, vr in validation_report.items() if not vr.is_valid
        ]
        error_df = pd.DataFrame(error_rows) if error_rows else pd.DataFrame({"Not": ["Hata yok"]})
        error_df.to_excel(writer, sheet_name="Hata Raporu", index=False)

    return output_path
