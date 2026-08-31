"""
Hisse/Kripto Tarama Sistemi - Tarayıcı Arayüzü

Çalıştırma:
    streamlit run app.py

Bu, terminale komut yazmadan, tıklayarak tarama yapmanı ve sonuçları
tabloda görmeni sağlar. Excel raporu yine oluşur (reports/ klasörüne),
ayrıca burada indirme butonu da var.
"""
import io
import logging
import os
import sys
import time
import traceback
from datetime import datetime

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from main_scan import run_scan

st.set_page_config(page_title="Hisse & Kripto Tarama Sistemi", layout="wide", page_icon="📈")


# --- Çalışma sırasında oluşan log satırlarını yakalayıp ekranda göstermek için ---
class StreamlitLogHandler(logging.Handler):
    def __init__(self, container):
        super().__init__()
        self.container = container
        self.lines = []

    def emit(self, record):
        self.lines.append(self.format(record))
        # Sadece son 25 satırı göster, terminal gibi kayan bir görünüm
        self.container.code("\n".join(self.lines[-25:]), language=None)


st.title("📈 Hisse & Kripto Tarama Sistemi")
st.caption("Teknik + temel analiz + göreceli güç + risk metrikleri birleşik skorlama")

# ============ SOL PANEL: AYARLAR ============
with st.sidebar:
    st.header("Tarama Ayarları")

    markets_labels = {"ABD Hisseleri (S&P 100)": "us", "BIST": "bist", "Kripto Paralar": "crypto", "Altın": "gold"}
    selected_labels = st.multiselect(
        "Hangi piyasalar taransın?",
        options=list(markets_labels.keys()),
        default=list(markets_labels.keys()),
    )
    selected_markets = [markets_labels[l] for l in selected_labels]

    st.divider()
    st.subheader("Hız / Kapsam")
    use_cache = st.checkbox("Önbelleği kullan (daha hızlı)", value=True,
                             help="Kapatırsan her seferinde tüm veriler internetten yeniden çekilir")
    skip_fundamentals = st.checkbox("Temel analizi atla (çok daha hızlı)", value=False,
                                     help="P/E, ROE gibi verileri çekmez, sadece teknik + göreceli güç analizine bakar")
    skip_news = st.checkbox("Haber analizini atla (daha hızlı)", value=False,
                             help="Sembol bazlı ve makro haber başlıklarını çekmez")

    st.divider()
    st.subheader("Filtreler")
    min_score = st.slider("Minimum skor (|değer|)", 0.0, 1.0, 0.15, 0.05)
    signal_choice = st.radio("Sinyal yönü", ["Hepsi", "Sadece AL", "Sadece SAT"], horizontal=False)
    min_market_cap_b = st.number_input("Min. piyasa değeri (milyar $, boş=filtre yok)",
                                        min_value=0.0, value=0.0, step=0.5)
    max_pe = st.number_input("Maks. F/K oranı (boş/0=filtre yok)", min_value=0.0, value=0.0, step=5.0)

    st.divider()
    st.subheader("Otomasyon")
    auto_refresh = st.checkbox("Sembol listelerini otomatik güncelle", value=True,
                                help="7 günden eski listeleri taramadan önce otomatik tazeler")
    update_journal = st.checkbox("Sinyal günlüğüne kaydet (performans takibi)", value=True)
    send_notify = st.checkbox("Telegram bildirimi gönder (yapılandırılmışsa)", value=True,
                               help="TELEGRAM_BOT_TOKEN ortam değişkeni yoksa otomatik atlanır, hata vermez")

    st.divider()
    run_clicked = st.button("🔍 Taramayı Başlat", type="primary", use_container_width=True)


# ============ SAĞ PANEL: SONUÇLAR ============
if "last_report_path" not in st.session_state:
    st.session_state.last_report_path = None

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

    st.info("Tarama başladı — piyasa sayısına ve internet hızına göre birkaç dakika sürebilir. "
            "Lütfen pencereyi kapatma.")
    progress_area = st.empty()

    handler = StreamlitLogHandler(progress_area)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    start = time.time()
    try:
        output_path = run_scan(
            markets=selected_markets,
            use_cache=use_cache,
            skip_fundamentals=skip_fundamentals,
            skip_news=skip_news,
            filter_overrides=overrides,
            auto_refresh_universe=auto_refresh,
            send_notification=send_notify,
            update_journal=update_journal,
        )
        st.session_state.last_report_path = output_path
        elapsed = time.time() - start
        st.success(f"✅ Tarama tamamlandı! ({elapsed:.0f} saniye)")
    except Exception as e:
        st.error(f"Tarama sırasında hata oluştu: {e}")
        st.code(traceback.format_exc())
    finally:
        root_logger.removeHandler(handler)


# ============ SONUÇLARI GÖSTER ============
if st.session_state.last_report_path and os.path.exists(st.session_state.last_report_path):
    path = st.session_state.last_report_path
    st.divider()
    st.subheader("Sonuçlar")

    with open(path, "rb") as f:
        excel_bytes = f.read()
    st.download_button(
        "⬇️ Excel raporunu indir",
        data=excel_bytes,
        file_name=os.path.basename(path),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    sheets = pd.read_excel(path, sheet_name=None)
    tab_names = [name for name in sheets.keys()]
    tabs = st.tabs(tab_names)

    for tab, name in zip(tabs, tab_names):
        with tab:
            df = sheets[name]
            if df.empty:
                st.write("Bu sayfada veri yok.")
                continue

            if "Skor" in df.columns:
                styled = df.style.background_gradient(
                    subset=["Skor"], cmap="RdYlGn", vmin=-1, vmax=1
                )
                st.dataframe(styled, use_container_width=True, height=500)
            else:
                st.dataframe(df, use_container_width=True, height=500)
else:
    st.info("Soldaki ayarları seç ve **'Taramayı Başlat'** butonuna bas.")
    st.markdown("""
    **İlk kez mi kullanıyorsun?**
    1. Soldan taramak istediğin piyasaları seç (ABD / BIST / Kripto)
    2. Hızlı bir deneme için "Temel analizi atla" kutucuğunu işaretle
    3. "Taramayı Başlat" butonuna bas
    4. Birkaç dakika sonra aşağıda sonuç tabloları ve indirme butonu görünecek
    """)
