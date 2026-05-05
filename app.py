import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
import requests
import warnings
from datetime import datetime
from tradingview_screener import Query, Column

# Konfigurasi Pandas
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD TIER ARA Hunter", layout="wide", page_icon="👁️")

# --- KONFIGURASI TELEGRAM PERMANEN ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"

st.title("👁️ GOD TIER ARA Hunter (V10.1)")
st.caption("Auto-Scan | Smart Money Concepts | Telegram Alert Enabled")

# --- SIDEBAR UNTUK CHAT ID ---
with st.sidebar:
    st.header("📲 Notifikasi Telegram")
    # Chat ID tetap perlu diinput atau bisa Anda ganti '12345678' di bawah dengan ID asli Anda
    tele_chat_id = st.text_input("Masukkan Chat ID Anda:", placeholder="Contoh: 12345678")
    aktifkan_tele = st.toggle("Aktifkan Alarm Telegram", value=True)
    st.info("Dapatkan Chat ID melalui bot @userinfobot di Telegram.")

def kirim_telegram(pesan):
    if aktifkan_tele and tele_chat_id:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        payload = {"chat_id": tele_chat_id, "text": pesan, "parse_mode": "HTML"}
        try:
            requests.post(url, data=payload, timeout=5)
        except:
            pass

# --- UI PENGATURAN FILTER ---
with st.expander("⚙️ Pengaturan Algoritma", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        opsi_mc = st.selectbox("Market Cap", ["Semua", "Mulai Rp 500 M", "Mulai Rp 1 T", "Mulai Rp 10 T"], index=2)
    with col2:
        min_kenaikan = st.number_input("Min Naik (%)", value=2.0, step=0.5)
    with col3:
        min_vol_ratio = st.number_input("Min Vol Loncat (x)", value=1.5, step=0.5)

# Mapping Market Cap
min_mc_angka = {"Semua": 0, "Mulai Rp 500 M": 5e11, "Mulai Rp 1 T": 1e12, "Mulai Rp 10 T": 1e13}[opsi_mc]

st.divider()

col_btn, col_auto = st.columns([2, 1])
with col_btn:
    tombol_manual = st.button("🚀 EKSEKUSI RADAR", use_container_width=True, type="primary")
with col_auto:
    mode_auto = st.toggle("🔄 Auto-Scan 15 Menit")

# --- FUNGSI SMART MONEY SUPPORT ---
def proses_smc(ticker):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="6mo")
        if df.empty: return None, 0
        df['Price_Bin'] = df['Close'].round(-1)
        poc_price = df.groupby('Price_Bin')['Volume'].sum().idxmax()
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index[-60:], open=df.index[-60:], high=df['High'][-60:], low=df['Low'][-60:], close=df['Close'][-60:], name="Harga"))
        fig.add_trace(go.Scatter(x=[df.index[-60], df.index[-1]], y=[poc_price, poc_price], mode="lines", line=dict(color="cyan", width=2, dash="dot"), name="SMC Support"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        return fig, poc_price
    except: return None, 0

# --- LOGIKA UTAMA ---
if tombol_manual or mode_auto:
    st.caption(f"Last Scan: {datetime.now().strftime('%H:%M:%S')} WIB")
    
    try:
        query = (Query().set_markets('indonesia')
                 .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'RSI', 'SMA50', 'SMA200', 'price_52_week_high', 'market_cap_basic', 'sector', 'open', 'high', 'low')
                 .where(Column('change') >= min_kenaikan, Column('close') > Column('SMA50')))
        
        _, df = query.get_scanner_data()
        
        if not df.empty:
            df = df[df['market_cap_basic'] >= min_mc_angka]
            df['vol_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0, 1)
            df = df[df['vol_ratio'] >= min_vol_ratio]
            
            # Anti-Trap & Sorting
            df['is_trap'] = (df['high'] - df[['open', 'close']].max(axis=1)) > (2 * abs(df['close'] - df['open']).replace(0, 0.01))
            df = df.sort_values(by='change', ascending=False).reset_index(drop=True)
            
            if not df.empty:
                st.success(f"👁️ Radar menemukan {len(df)} saham potensial.")
                pesan_tele = f"👁️ <b>GOD TIER ALERT</b>\n🕒 {datetime.now().strftime('%H:%M')}\n\n"
                
                for idx, row in df.iterrows():
                    saham = row['name']
                    fig, poc = proses_smc(saham)
                    
                    # UI Streamlit
                    with st.container():
                        st.subheader(f"Rank #{idx+1}: {saham} (+{round(row['change'],2)}%)")
                        if row['is_trap']: st.error("⚠️ TRAP DETECTED")
                        else: st.success("✅ CLEAN ACCUMULATION")
                        
                        col_a, col_b, col_c = st.columns(3)
                        col_a.metric("Harga", f"{int(row['close'])}")
                        col_b.metric("SMC Support", f"{int(poc)}")
                        col_c.metric("Vol Ratio", f"{round(row['vol_ratio'],1)}x")
                        
                        if fig: st.plotly_chart(fig, use_container_width=True)
                    
                    # Isi Pesan Tele (Hanya 3 teratas yang tidak trap)
                    if idx < 3 and not row['is_trap']:
                        pesan_tele += f"🚀 <b>{saham}</b>\nHarga: {int(row['close'])}\nNaik: {round(row['change'],2)}%\nSupport: {int(poc)}\n\n"
                
                if aktifkan_tele: kirim_telegram(pesan_tele)
        else:
            st.info("Belum ada sinyal terdeteksi.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- TIMER ---
if mode_auto:
    t_minus = st.empty()
    for s in range(900, 0, -1):
        m, sec = divmod(s, 60)
        t_minus.markdown(f"### ⏳ Next Scan: {m:02d}:{sec:02d}")
        time.sleep(1)
    st.rerun()