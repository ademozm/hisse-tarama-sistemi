"""
Hisse/Kripto Tarama Sistemi - Görsel Tarayıcı Panel

Çalıştırma:
    streamlit run app.py

Grafikler için: reporting/dashboard_charts.py (Streamlit'ten bağımsız,
pytest ile test edilen saf fonksiyonlar). Bu dosya sadece arayüz/etkileşim
kodudur.
"""
import ast
import logging
import os
import sys
import time
import traceback

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from main_scan import run_scan
from data_pipeline import cache
from analysis import indicators
from reporting import dashboard_charts as charts

st.set_page_config(page_title="Hisse & Kripto Tarama Sistemi", layout="wide", page_icon="📈")

# ============ ÖZEL CSS: kart görünümü, renkler, boşluklar ============
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; max-width: 1400px; }
    div[data-testid="stMetric"] {
        background: rgba(120,120,120,0.06);
        border: 1px solid rgba(120,120,120,0.15);
        border-radius: 10px;
        padding: 12px 16px;
    }
    .kpi-good { color: #16a34a !important; }
    .kpi-bad { color: #dc2626 !important; }
    .news-card {
        border: 1px solid rgba(120,120,120,0.15);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    .event-card {
        border-left: 4px solid #f59e0b;
        background: rgba(245,158,11,0.08);
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    h1, h2, h3 { letter-spacing: -0.3px; }
</style>
""", unsafe_allow_html=True)


class StreamlitLogHandler(logging.Handler):
    def __init__(self, container):
        super().__init__()
        self.container = container
        self.lines = []

    def emit(self, record):
        self.lines.append(self.format(record))
        self.container.code("\n".join(self.lines[-25:]), language=None)


def _parse_list_cell(value):
    """Excel'e yazılırken string'e dönüşen Python listelerini ([1.2, 3.4] gibi) geri çevirir."""
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip().startswith("["):
        return []
    try:
        return [float(x) for x in ast.literal_eval(value)]
    except Exception:
        return []


st.title("📈 Hisse & Kripto Tarama Sistemi")
st.caption("Teknik + temel analiz + göreceli güç + risk + haber + grid/DCA — birleşik skorlama, çok kaynaklı doğrulama")

# ============ SOL PANEL: AYARLAR ============
with st.sidebar:
    st.header("Tarama Ayarları")

    markets_labels = {"ABD Hisseleri (S&P 100)": "us", "BIST": "bist", "Kripto Paralar": "crypto",
                       "Emtialar (Altın/Gümüş/Petrol/Doğalgaz)": "emtia", "Döviz Kurları (USD/TRY dahil)": "forex"}
    selected_labels = st.multiselect("Hangi piyasalar taransın?", options=list(markets_labels.keys()),
                                      default=list(markets_labels.keys()))
    selected_markets = [markets_labels[l] for l in selected_labels]

    st.divider()
    st.subheader("Hız / Kapsam")
    use_cache = st.checkbox("Önbelleği kullan (daha hızlı)", value=True)
    skip_fundamentals = st.checkbox("Temel analizi atla (çok daha hızlı)", value=False)
    skip_news = st.checkbox("Haber analizini atla (daha hızlı)", value=False)

    st.divider()
    st.subheader("Filtreler")
    min_score = st.slider("Minimum skor (|değer|)", 0.0, 1.0, 0.15, 0.05)
    signal_choice = st.radio("Sinyal yönü", ["Hepsi", "Sadece AL", "Sadece SAT"])
    min_market_cap_b = st.number_input("Min. piyasa değeri (milyar $, 0=filtre yok)", min_value=0.0, value=0.0, step=0.5)
    max_pe = st.number_input("Maks. F/K oranı (0=filtre yok)", min_value=0.0, value=0.0, step=5.0)

    st.divider()
    st.subheader("Pozisyon Büyüklüğü")
    account_size = st.number_input("Varsayımsal hesap büyüklüğü ($)", min_value=100.0, value=10000.0, step=500.0)
    risk_pct = st.slider("İşlem başına risk (%)", 0.25, 5.0, 1.0, 0.25)

    st.divider()
    st.subheader("Otomasyon")
    auto_refresh = st.checkbox("Sembol listelerini otomatik güncelle", value=True)
    update_journal = st.checkbox("Sinyal günlüğüne kaydet", value=True)
    send_notify = st.checkbox("Telegram bildirimi gönder (varsa)", value=True)

    st.divider()
    run_clicked = st.button("🔍 Taramayı Başlat", type="primary", use_container_width=True)


def _find_latest_report() -> str | None:
    """reports/ klasöründeki en son (dosya adına göre en yeni) Excel raporunu bulur.
    GitHub Actions gibi otomatik taramalar sonucu oluşan raporu, panel
    açılır açılmaz göstermek için kullanılır."""
    if not os.path.isdir(config.REPORTS_DIR):
        return None
    xlsx_files = [f for f in os.listdir(config.REPORTS_DIR) if f.endswith(".xlsx") and f.startswith("tarama_")]
    if not xlsx_files:
        return None
    xlsx_files.sort(reverse=True)  # dosya adı YYYYMMDD_HHMMSS içerdiği için alfabetik = kronolojik
    return os.path.join(config.REPORTS_DIR, xlsx_files[0])


if "last_report_path" not in st.session_state:
    # Panel ilk açıldığında (örn. Telegram linkinden), elle tarama yapmadan
    # önce otomatik taramanın (GitHub Actions) en son ürettiği raporu göster
    st.session_state.last_report_path = _find_latest_report()

if run_clicked:
    if not selected_markets:
        st.error("En az bir piyasa seçmelisin.")
        st.stop()

    allowed_signals = None
    if signal_choice == "Sadece AL":
        allowed_signals = [1]
    elif signal_choice == "Sadece SAT":
        allowed_signals = [-1]

    overrides = {
        "min_composite_score": min_score,
        "allowed_signals": allowed_signals,
        "min_market_cap": min_market_cap_b * 1_000_000_000 if min_market_cap_b > 0 else None,
        "max_pe": max_pe if max_pe > 0 else None,
    }

    st.info("Tarama başladı — birkaç dakika sürebilir. Lütfen pencereyi kapatma.")
    progress_area = st.empty()
    handler = StreamlitLogHandler(progress_area)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    start = time.time()
    try:
        output_path = run_scan(
            markets=selected_markets, use_cache=use_cache, skip_fundamentals=skip_fundamentals,
            skip_news=skip_news, filter_overrides=overrides, auto_refresh_universe=auto_refresh,
            send_notification=send_notify, update_journal=update_journal,
            account_size=account_size, risk_per_trade_pct=risk_pct,
        )
        st.session_state.last_report_path = output_path
        st.success(f"✅ Tarama tamamlandı! ({time.time() - start:.0f} saniye)")
    except Exception as e:
        st.error(f"Tarama sırasında hata oluştu: {e}")
        st.code(traceback.format_exc())
    finally:
        root_logger.removeHandler(handler)


# ============ SONUÇLARI GÖSTER ============
if st.session_state.last_report_path and os.path.exists(st.session_state.last_report_path):
    path = st.session_state.last_report_path
    sheets = pd.read_excel(path, sheet_name=None)
    ozet = sheets.get("Özet", pd.DataFrame())

    report_time = os.path.getmtime(path)
    report_dt = pd.Timestamp.fromtimestamp(report_time)
    if not run_clicked:
        st.caption(f"📄 Otomatik bulunan en son rapor gösteriliyor — {report_dt.strftime('%d.%m.%Y %H:%M')} "
                   f"tarihli (muhtemelen otomatik/bulut taramasından). Kendi kriterlerinle yeni bir tarama "
                   f"için soldan ayarları seçip 'Taramayı Başlat'a bas.")

    st.divider()
    with open(path, "rb") as f:
        st.download_button("⬇️ Excel raporunu indir", data=f.read(), file_name=os.path.basename(path),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ---- KPI kartları ----
    if not ozet.empty:
        al_count = (ozet["Sinyal"] == "AL").sum()
        sat_count = (ozet["Sinyal"] == "SAT").sum()
        avg_score = ozet["Skor"].abs().mean()
        supheli_count = (ozet.get("Veri Şüpheli mi", pd.Series(dtype=str)) == "Evet").sum()
        takvim_df = sheets.get("Ekonomik Takvim", pd.DataFrame())
        yaklasan_olay = len(takvim_df) if "Tarih" in takvim_df.columns else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Toplam Sinyal", len(ozet))
        c2.metric("AL Sinyali", al_count)
        c3.metric("SAT Sinyali", sat_count)
        c4.metric("Ort. |Skor|", f"{avg_score:.2f}")
        c5.metric("Yaklaşan Önemli Olay", yaklasan_olay, delta="⚠️" if yaklasan_olay > 0 else None)
        if supheli_count > 0:
            st.warning(f"⚠️ {supheli_count} sembolde yfinance/Stooq veri uyuşmazlığı tespit edildi — 'Piyasalar' sekmesinde 'Veri Şüpheli mi' sütununa bak.")

    st.divider()

    tab_names = ["📊 Genel Bakış", "📈 Grafik İnceleme", "💼 Piyasalar", "🔬 Temel & Risk & Gelişmiş",
                 "🎯 Grid & DCA", "📰 Haberler", "📅 Ekonomik Takvim", "📜 Geçmiş Performans", "⚠️ Hata Raporu"]
    tabs = st.tabs(tab_names)

    # ---- 1) Genel Bakış ----
    with tabs[0]:
        if ozet.empty:
            st.info("Bu taramada sinyal üreten sembol bulunamadı.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(charts.market_breakdown_pie(ozet), use_container_width=True)
            with col2:
                st.plotly_chart(charts.score_histogram(ozet), use_container_width=True)
            st.plotly_chart(charts.top_signals_bar(ozet, n=10), use_container_width=True)

    # ---- 2) Grafik İnceleme (candlestick + EMA + destek/direnç) ----
    with tabs[1]:
        gelismis = sheets.get("Gelişmiş Göstergeler", pd.DataFrame())
        if ozet.empty:
            st.info("Grafik için önce bir tarama yapmalısın.")
        else:
            symbol_options = ozet["Sembol"].tolist()
            selected_symbol = st.selectbox("Sembol seç", symbol_options)

            ohlc = cache.get_cached(selected_symbol, config.FETCH_INTERVAL, ttl_minutes=999999)
            if ohlc is None:
                st.warning("Bu sembol için önbellekte fiyat verisi bulunamadı (cache temizlenmiş olabilir).")
            else:
                ema_fast = indicators.ema(ohlc["Close"], 12)
                ema_slow = indicators.ema(ohlc["Close"], 26)

                support_levels, resistance_levels = [], []
                if not gelismis.empty and "Sembol" in gelismis.columns:
                    row = gelismis[gelismis["Sembol"] == selected_symbol]
                    if not row.empty:
                        support_levels = _parse_list_cell(row.iloc[0].get("Destek Seviyeleri"))
                        resistance_levels = _parse_list_cell(row.iloc[0].get("Direnç Seviyeleri"))

                fig = charts.candlestick_chart(
                    ohlc.tail(150), ema_fast=ema_fast.tail(150), ema_slow=ema_slow.tail(150),
                    support_levels=support_levels, resistance_levels=resistance_levels,
                    title=f"{selected_symbol} — Fiyat + EMA(12/26) + Destek/Direnç",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.plotly_chart(charts.volume_bar(ohlc.tail(150)), use_container_width=True)

                sym_row = ozet[ozet["Sembol"] == selected_symbol]
                if not sym_row.empty:
                    r = sym_row.iloc[0]
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("Sinyal", r.get("Sinyal", "-"))
                    mc2.metric("Skor", f"{r.get('Skor', 0):.3f}")
                    mc3.metric("RSI", f"{r.get('RSI', 0):.1f}" if pd.notna(r.get("RSI")) else "-")
                    mc4.metric("ADX", f"{r.get('ADX', 0):.1f}" if pd.notna(r.get("ADX")) else "-")

    # ---- 3) Piyasalar (ABD/BIST/Kripto/Emtia/Döviz tabloları) ----
    with tabs[2]:
        market_tab_names = [n for n in ["ABD", "BIST", "Kripto", "Emtialar", "Döviz"] if n in sheets]
        if market_tab_names:
            market_tabs = st.tabs(market_tab_names)
            for mtab, mname in zip(market_tabs, market_tab_names):
                with mtab:
                    df = sheets[mname]
                    if df.empty:
                        st.write("Bu piyasada sinyal bulunamadı.")
                    elif "Skor" in df.columns:
                        st.dataframe(df.style.background_gradient(subset=["Skor"], cmap="RdYlGn", vmin=-1, vmax=1),
                                     use_container_width=True, height=500)
                    else:
                        st.dataframe(df, use_container_width=True, height=500)

    # ---- 4) Temel & Risk & Gelişmiş Göstergeler ----
    with tabs[3]:
        for sheet_name in ["Temel Analiz", "Risk Metrikleri", "Gelişmiş Göstergeler"]:
            df = sheets.get(sheet_name, pd.DataFrame())
            st.subheader(sheet_name)
            if df.empty:
                st.write("Veri yok.")
            else:
                st.dataframe(df, use_container_width=True, height=350)
            st.divider()

    # ---- 5) Grid & DCA ----
    with tabs[4]:
        grid_df = sheets.get("Grid Planı", pd.DataFrame())
        dca_df = sheets.get("DCA Planı", pd.DataFrame())

        st.subheader("Grid Planı (yatay/range piyasalar için)")
        if grid_df.empty or "Sembol" not in grid_df.columns:
            st.info("Bu taramada grid stratejisine uygun (range rejiminde) sembol bulunamadı.")
        else:
            grid_symbols = grid_df["Sembol"].unique().tolist()
            sel_grid_symbol = st.selectbox("Sembol seç", grid_symbols, key="grid_symbol")
            st.plotly_chart(charts.grid_ladder_chart(grid_df[grid_df["Sembol"] == sel_grid_symbol]),
                             use_container_width=True)
            st.dataframe(grid_df[grid_df["Sembol"] == sel_grid_symbol], use_container_width=True)

        st.divider()
        st.subheader("DCA (Kademeli Alım) Planı")
        if dca_df.empty or "Sembol" not in dca_df.columns:
            st.info("Bu taramada AL sinyali üreten sembol bulunamadı.")
        else:
            dca_symbols = dca_df["Sembol"].unique().tolist()
            sel_dca_symbol = st.selectbox("Sembol seç", dca_symbols, key="dca_symbol")
            st.plotly_chart(charts.dca_steps_chart(dca_df[dca_df["Sembol"] == sel_dca_symbol]),
                             use_container_width=True)
            st.dataframe(dca_df[dca_df["Sembol"] == sel_dca_symbol], use_container_width=True)

    # ---- 6) Haberler ----
    with tabs[5]:
        haberler = sheets.get("Haberler", pd.DataFrame())
        if haberler.empty:
            st.info("Bu taramada haber verisi bulunamadı.")
        else:
            for _, row in haberler.iterrows():
                sentiment = row.get("Haber Tonu", 0)
                sentiment = 0 if pd.isna(sentiment) else sentiment
                renk = "#16a34a" if sentiment > 0.1 else ("#dc2626" if sentiment < -0.1 else "#6b7280")
                sembol_etiketi = f"<b>{row.get('Sembol', '')}</b> — " if row.get("Sembol") else ""
                st.markdown(f"""
                <div class="news-card">
                    <span style="color:{renk}; font-weight:600;">●</span>
                    {sembol_etiketi}{row.get('Başlık', '')}
                    <br><span style="color:#888; font-size:0.85em;">{row.get('Kaynak', '')} · {row.get('Yayıncı', '')}</span>
                </div>
                """, unsafe_allow_html=True)
            st.caption("Haber tonu basit anahtar-kelime sayımıdır, gerçek NLP değildir — kaba bir gösterge olarak değerlendirin.")

    # ---- 7) Ekonomik Takvim ----
    with tabs[6]:
        takvim = sheets.get("Ekonomik Takvim", pd.DataFrame())
        if takvim.empty or "Tarih" not in takvim.columns:
            st.info("Önümüzdeki 14 gün içinde bilinen önemli bir ekonomik olay yok.")
        else:
            for _, row in takvim.sort_values("Kalan Gün").iterrows():
                st.markdown(f"""
                <div class="event-card">
                    <b>{row['Tarih']}</b> ({int(row['Kalan Gün'])} gün kaldı) — {row['Olay']}
                    <br><span style="color:#888; font-size:0.85em;">Önem: {row['Önem']}</span>
                </div>
                """, unsafe_allow_html=True)

    # ---- 8) Geçmiş Performans ----
    with tabs[7]:
        perf = sheets.get("Performans Geçmişi", pd.DataFrame())
        if perf.empty:
            st.info("Henüz yeterli sinyal geçmişi yok — sistem birkaç tarama sonra performans istatistiği üretmeye başlar.")
        else:
            st.dataframe(perf, use_container_width=True)

    # ---- 9) Hata Raporu ----
    with tabs[8]:
        hata = sheets.get("Hata Raporu", pd.DataFrame())
        if hata.empty or "Sembol" not in hata.columns:
            st.success("Bu taramada hata/geçersiz veri yok.")
        else:
            st.dataframe(hata, use_container_width=True)

else:
    st.info("Soldaki ayarları seç ve **'Taramayı Başlat'** butonuna bas.")
    st.markdown("""
    **İlk kez mi kullanıyorsun?**
    1. Soldan taramak istediğin piyasaları seç (ABD / BIST / Kripto / Emtia / Döviz)
    2. Hızlı bir deneme için "Temel analizi atla" kutucuğunu işaretle
    3. "Taramayı Başlat" butonuna bas
    4. Birkaç dakika sonra: KPI kartları, grafikler ve sekmeli detaylı sonuçlar burada görünecek
    """)
