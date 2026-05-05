import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
import requests
import random
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI PANDAS ---
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE ARA Hunter", layout="centered", page_icon="🏦")

# --- TOKEN & KONFIGURASI PERMANEN ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"

st.title("🏦 GOD MODE ARA Hunter (V11.0)")
st.caption("ATR Volatility Engine | Risk Manager | News Sentiment | SMC Pro")

# --- SIDEBAR: RISK & NOTIF ---
with st.sidebar:
    st.header("💼 Risk Management")
    total_modal = st.number_input("Total Modal (Rp)", value=10000000, step=1000000)
    risk_per_trade = st.slider("Risiko Per Trade (%)", 1, 5, 2)
    st.divider()
    st.header("📲 Telegram Alerts")
    tele_chat_id = st.text_input("Chat ID Anda:", placeholder="Cek di @userinfobot")
    aktifkan_tele = st.toggle("Aktifkan Alarm", value=True)

# --- FUNGSI TOOLS ---
def kirim_telegram(pesan):
    if aktifkan_tele and tele_chat_id:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        payload = {"chat_id": tele_chat_id, "text": pesan, "parse_mode": "HTML"}
        try: requests.post(url, data=payload, timeout=5)
        except: pass

def hitung_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_cp = abs(df['High'] - df['Close'].shift())
    low_cp = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr.iloc[-1]

# --- FUNGSI CORE ANALISA ---
def get_advanced_analysis(ticker):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y") # 1 tahun untuk MA200 & ATR
        if df.empty or len(df) < 50: return None
        
        # 1. ATR & Dynamic Levels
        atr = hitung_atr(df)
        last_price = df['Close'].iloc[-1]
        
        # 2. SMC Support (POC)
        df['Price_Bin'] = df['Close'].round(-1)
        poc_price = df.groupby('Price_Bin')['Volume'].sum().idxmax()
        
        # 3. Trading Plan (ATR Based)
        # Entry di POC atau harga saat ini jika dekat
        stop_loss = int(last_price - (1.5 * atr))
        target_profit = int(last_price + (3 * atr))
        risk_amount = last_price - stop_loss
        
        # 4. Position Sizing
        max_risk_rp = total_modal * (risk_per_trade / 100)
        lot_size = int((max_risk_rp / risk_amount) / 100) if risk_amount > 0 else 0
        
        # 5. News
        news = s.news[:3]
        
        # 6. Chart
        df_p = df.tail(50)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price")])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc_price, poc_price], line=dict(color="cyan", width=2, dash="dot"), name="SMC POC"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        
        return {
            "fig": fig, "poc": poc_price, "atr": atr, "sl": stop_loss, "tp": target_profit, 
            "lots": lot_size, "news": news, "risk_rp": max_risk_rp
        }
    except: return None

# --- UI FILTER ---
with st.expander("🔬 Tuning Algoritma God Mode"):
    c1, c2, c3 = st.columns(3)
    with c1: min_naik = st.number_input("Min Naik (%)", value=2.5)
    with c2: min_vol = st.number_input("Min Vol Ratio", value=2.0)
    with c3: filter_mc = st.selectbox("Market Cap", ["Semua", "Mid-Big (>1T)"], index=1)

min_mc = 1e12 if "Mid-Big" in filter_mc else 0

st.divider()
btn_scan = st.button("🚀 AKTIFKAN GOD-ENGINE", use_container_width=True, type="primary")

# --- EKSEKUSI ---
if btn_scan:
    st.caption(f"Radar Active: {datetime.now().strftime('%H:%M:%S')}")
    try:
        q = (Query().set_markets('indonesia')
             .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'SMA50', 'SMA200', 'market_cap_basic', 'open', 'high')
             .where(Column('change') >= min_naik, Column('close') > Column('SMA50'), Column('close') > Column('SMA200')))
        
        _, df = q.get_scanner_data()
        
        if not df.empty:
            df = df[df['market_cap_basic'] >= min_mc]
            df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
            df = df[df['v_ratio'] >= min_vol]
            df['is_trap'] = (df['high'] - df[['open', 'close']].max(axis=1)) > (2 * abs(df['close'] - df['open']).replace(0,0.01))
            
            df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
            
            if not df.empty:
                st.success(f"💎 {len(df)} Saham 'High Probability' Terdeteksi!")
                pesan_tele = f"🏦 <b>GOD MODE REPORT</b>\n\n"
                
                for idx, row in df.iterrows():
                    res = get_advanced_analysis(row['name'])
                    if res:
                        with st.container():
                            st.subheader(f"Rank #{idx+1}: {row['name']} (+{round(row['change'],2)}%)")
                            
                            # Validasi Bandar
                            if row['is_trap']: st.error("⚠️ STATUS: FAKE PUMP (Bandar Jualan)")
                            else: st.success("✅ STATUS: INSTITUTIONAL BUYING")
                            
                            # Row 1: Trading Plan
                            st.markdown("### 🎯 Trading Plan & Risk Management")
                            p1, p2, p3 = st.columns(3)
                            p1.warning(f"**Entry Area**\nRp {int(row['close'])}")
                            p2.success(f"**Target Profit (3x ATR)**\nRp {res['tp']}")
                            p3.error(f"**Stop Loss (1.5x ATR)**\nRp {res['sl']}")
                            
                            # Row 2: Position Sizing
                            st.info(f"💡 **Saran Alokasi:** Beli **{res['lots']} Lot** (Risiko Rp {int(res['risk_rp']):,})")
                            
                            # Row 3: Charts
                            st.plotly_chart(res['fig'], use_container_width=True)
                            
                            # Row 4: News Sentiment
                            if res['news']:
                                with st.expander("📰 Berita Terkait (Sentimen)"):
                                    for n in res['news']:
                                        st.write(f"**{n['title']}**")
                                        st.caption(f"Source: {n['publisher']}")
                            
                            # Telegram Data
                            if not row['is_trap']:
                                pesan_tele += f"🚀 <b>{row['name']}</b>\nEntry: {int(row['close'])}\nTP: {res['tp']}\nSL: {res['sl']}\nBeli: {res['lots']} Lot\n\n"
                            
                            st.divider()
                
                if aktifkan_tele: kirim_telegram(pesan_tele)
            else: st.info("Saringan ketat: Tidak ada saham lolos standar institusi.")
        else: st.info("Pasar tenang, tidak ada ledakan volume.")
    except Exception as e: st.error(f"Engine Error: {e}")