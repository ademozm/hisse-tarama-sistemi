import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data_pipeline import cache
from analysis import indicators
from reporting import dashboard_charts as charts
import dashboard_common as dc

st.set_page_config(page_title="Grafik İnceleme", layout="wide", page_icon="📈")
dc.inject_css()
st.title("📈 Grafik İnceleme")
st.caption("İnteraktif mum grafiği + EMA çizgileri + destek/direnç seviyeleri + hacim")

path, sheets = dc.require_report_or_stop()
ozet = sheets.get("Özet", pd.DataFrame())
gelismis = sheets.get("Gelişmiş Göstergeler", pd.DataFrame())

if ozet.empty:
    st.info("Bu taramada sinyal üreten sembol bulunamadı, grafik için gösterilecek bir şey yok.")
    st.stop()

symbol_options = ozet["Sembol"].tolist()
selected_symbol = st.selectbox("Sembol seç", symbol_options)

ohlc = cache.get_cached(selected_symbol, config.FETCH_INTERVAL, ttl_minutes=999999)
if ohlc is None:
    st.warning("Bu sembol için önbellekte fiyat verisi bulunamadı (cache temizlenmiş olabilir).")
    st.stop()

ema_fast = indicators.ema(ohlc["Close"], 12)
ema_slow = indicators.ema(ohlc["Close"], 26)

support_levels, resistance_levels = [], []
if not gelismis.empty and "Sembol" in gelismis.columns:
    row = gelismis[gelismis["Sembol"] == selected_symbol]
    if not row.empty:
        support_levels = dc.parse_list_cell(row.iloc[0].get("Destek Seviyeleri"))
        resistance_levels = dc.parse_list_cell(row.iloc[0].get("Direnç Seviyeleri"))

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
