import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
import requests
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI PANDAS ---
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE ARA Hunter", layout="centered", page_icon="🏦")

# --- TOKEN TELEGRAM PERMANEN ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"

st.title("🏦 GOD MODE ARA Hunter (V11.2)")
st.caption("Fixed News System | ATR Volatility | Risk Manager | SMC Pro")

# --- SIDEBAR ---
with st.sidebar:
    st.header("💼 Management Risiko")
    total_modal = st.number_input("Total Modal (Rp)", value=10000000, step=1000000)
    risk_per_trade = st.slider("Risiko Per Trade (%)", 1, 5, 2)
    st.divider()
    st.header("📲 Konfigurasi Telegram")
    tele_chat_id = st.text_input("Masukkan Chat ID Anda:", placeholder="Dapatkan di @userinfobot")
    st.info("Input Chat ID agar bot tahu ke mana harus mengirim sinyal.")

# --- TOOLS ---
def kirim_telegram(pesan):
    if tele_chat_id:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        payload = {"chat_id": tele_chat_id, "text": pesan, "parse_mode": "HTML"}
        try: requests.post(url, data=payload, timeout=5)
        except: pass

def hitung_atr(df, period=14):
    tr = pd.concat([df['High'] - df['Low'], 
                    abs(df['High'] - df['Close'].shift()), 
                    abs(df['Low'] - df['Close'].shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

# --- CORE ANALYSIS ---
def get_advanced_analysis(ticker):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        if df.empty or len(df) < 50: return None
        
        atr = hitung_atr(df)
        last_p = df['Close'].iloc[-1]
        
        # SMC Support
        df['Price_Bin'] = df['Close'].round(-1)
        poc = df.groupby('Price_Bin')['Volume'].sum().idxmax()
        
        # Risk Management
        sl = int(last_p - (1.5 * atr))
        tp = int(last_p + (3 * atr))
        lot = int(((total_modal * (risk_per_trade/100)) / (last_p - sl)) / 100) if (last_p - sl) > 0 else 0
        
        # Chart
        df_p = df.tail(40)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price")])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="cyan", width=2, dash="dot"), name="SMC POC"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        
        return {"fig": fig, "poc": poc, "sl": sl, "tp": tp, "lots": lot, "news": s.news[:3]}
    except: return None

# --- UI CONTROL ---
with st.expander("🔬 Filter Saringan"):
    c1, c2 = st.columns(2)
    with c1: min_naik = st.number_input("Min Naik (%)", value=2.0)
    with c2: filter_mc = st.selectbox("Market Cap", ["Semua", "Mid-Big (>1T)"], index=1)

st.divider()
col_send, _ = st.columns([1,1])
with col_send:
    manual_send = st.toggle("📤 Kirim Hasil ke Telegram", value=False)

btn_scan = st.button("🚀 JALANKAN SCAN", use_container_width=True, type="primary")

# --- EXECUTION ---
if btn_scan:
    st.caption(f"Radar Active: {datetime.now().strftime('%H:%M:%S')}")
    try:
        q = (Query().set_markets('indonesia')
             .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'SMA50', 'SMA200', 'market_cap_basic', 'open', 'high')
             .where(Column('change') >= min_naik, Column('close') > Column('SMA50'), Column('close') > Column('SMA200')))
        
        _, df = q.get_scanner_data()
        
        if not df.empty:
            min_mc = 1e12 if "Mid-Big" in filter_mc else 0
            df = df[df['market_cap_basic'] >= min_mc]
            df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
            df = df[df['v_ratio'] >= 1.5]
            df['is_trap'] = (df['high'] - df[['open', 'close']].max(axis=1)) > (2 * abs(df['close'] - df['open']).replace(0,0.01))
            
            df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
            
            if not df.empty:
                st.success(f"💎 Ditemukan {len(df)} Saham Jawara.")
                pesan_tele = f"🏦 <b>GOD MODE REPORT</b>\n\n"
                
                for idx, row in df.iterrows():
                    res = get_advanced_analysis(row['name'])
                    if res:
                        with st.container():
                            st.subheader(f"#{idx+1}: {row['name']} (+{round(row['change'],2)}%)")
                            
                            # Tampilan Trading Plan
                            p1, p2, p3 = st.columns(3)
                            p1.warning(f"**Entry**\nRp {int(row['close'])}")
                            p2.success(f"**Target**\nRp {res['tp']}")
                            p3.error(f"**Stop Loss**\nRp {res['sl']}")
                            
                            st.info(f"💡 Saran Alokasi: **{res['lots']} Lot**")
                            st.plotly_chart(res['fig'], use_container_width=True)
                            
                            # --- FITUR BERITA (NEWS) ---
                            if res['news']:
                                with st.expander("📰 Berita Terkait & Sentimen"):
                                    for n in res['news']:
                                        st.write(f"**{n['title']}**")
                                        st.caption(f"Source: {n['publisher']} | [Baca Berita]({n['link']})")
                            else:
                                st.caption("ℹ️ Tidak ada berita terbaru untuk saham ini dalam 24 jam terakhir.")
                            
                            if not row['is_trap']:
                                pesan_tele += f"🚀 <b>{row['name']}</b>\nEntry: {int(row['close'])}\nTarget: {res['tp']}\nSL: {res['sl']}\nBeli: {res['lots']} Lot\n\n"
                            st.divider()
                
                if manual_send:
                    kirim_telegram(pesan_tele)
                    st.toast("✅ Terkirim ke Telegram!")
            else: st.info("Saringan ketat: Tidak ada saham lolos.")
        else: st.info("Pasar sepi.")
    except Exception as e: st.error(f"Error: {e}")