import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
import requests
import warnings
from datetime import datetime
from tradingview_screener import Query, Column

# Konfigurasi Pandas & UI
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD TIER ARA Hunter", layout="centered", page_icon="👁️")

# --- KONFIGURASI TELEGRAM PERMANEN ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"

st.title("👁️ GOD TIER ARA Hunter (V10.2)")
st.caption("Optimized Performance | Top 5 Focus | Smart Money Support")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📲 Notifikasi Telegram")
    tele_chat_id = st.text_input("Masukkan Chat ID Anda:", placeholder="Cek di @userinfobot")
    aktifkan_tele = st.toggle("Aktifkan Alarm Telegram", value=True)
    st.divider()
    st.info("Aplikasi sekarang hanya menampilkan 5 saham dengan skor tertinggi untuk menjaga akurasi analisa.")

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
mc_map = {"Semua": 0, "Mulai Rp 500 M": 5e11, "Mulai Rp 1 T": 1e12, "Mulai Rp 10 T": 1e13}
min_mc_angka = mc_map[opsi_mc]

st.divider()

col_btn, col_auto = st.columns([2, 1])
with col_btn:
    tombol_manual = st.button("🚀 SCAN TOP 5 SAHAM", use_container_width=True, type="primary")
with col_auto:
    mode_auto = st.toggle("🔄 Auto-Scan 15 Menit")

# --- FUNGSI TELEGRAM ---
def kirim_telegram(pesan):
    if aktifkan_tele and tele_chat_id:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        payload = {"chat_id": tele_chat_id, "text": pesan, "parse_mode": "HTML"}
        try: requests.post(url, data=payload, timeout=5)
        except: pass

# --- FUNGSI SMART MONEY SUPPORT & CHART FIX ---
def proses_smc(ticker):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="6mo")
        if df.empty or len(df) < 20: return None, 0
        
        # Hitung POC (Point of Control)
        df['Price_Bin'] = df['Close'].round(-1)
        poc_price = df.groupby('Price_Bin')['Volume'].sum().idxmax()
        
        # Ambil 40 bar terakhir untuk grafik agar tidak terlalu padat
        df_plot = df.tail(40)
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_plot.index, 
            open=df_plot['Open'], 
            high=df_plot['High'], 
            low=df_plot['Low'], 
            close=df_plot['Close'], 
            name="Price"
        ))
        
        # Garis SMC Support
        fig.add_trace(go.Scatter(
            x=[df_plot.index[0], df_plot.index[-1]], 
            y=[poc_price, poc_price], 
            mode="lines", 
            line=dict(color="cyan", width=2, dash="dot"), 
            name="SMC Support"
        ))
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), 
            height=300, 
            xaxis_rangeslider_visible=False, 
            template="plotly_dark",
            showlegend=False
        )
        return fig, poc_price
    except: 
        return None, 0

# --- LOGIKA UTAMA ---
if tombol_manual or mode_auto:
    st.caption(f"Last Scan: {datetime.now().strftime('%H:%M:%S')} WIB")
    
    try:
        # TradingView Scan
        query = (Query().set_markets('indonesia')
                 .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'RSI', 'SMA50', 'open', 'high', 'low', 'market_cap_basic')
                 .where(Column('change') >= min_kenaikan, Column('close') > Column('SMA50')))
        
        _, df = query.get_scanner_data()
        
        if not df.empty:
            # Filter Market Cap & Volume Ratio
            df = df[df['market_cap_basic'] >= min_mc_angka]
            df['vol_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0, 1)
            df = df[df['vol_ratio'] >= min_vol_ratio]
            
            # Anti-Trap Logic
            df['is_trap'] = (df['high'] - df[['open', 'close']].max(axis=1)) > (2 * abs(df['close'] - df['open']).replace(0, 0.01))
            
            # Sorting & LIMIT TOP 5
            df = df.sort_values(by='change', ascending=False).head(5).reset_index(drop=True)
            
            if not df.empty:
                st.success(f"🔥 Radar mengunci {len(df)} saham terbaik hari ini.")
                pesan_tele = f"👁️ <b>TOP 5 GOD TIER ALERTS</b>\n🕒 {datetime.now().strftime('%H:%M')}\n\n"
                
                for idx, row in df.iterrows():
                    saham = row['name']
                    # Load chart & SMC
                    with st.spinner(f"Menganalisa {saham}..."):
                        fig, poc = proses_smc(saham)
                    
                    # Tampilan UI
                    with st.container():
                        medali = ["🏆", "🥈", "🥉", "📌", "📌"][idx]
                        st.subheader(f"{medali} Rank #{idx+1}: {saham} (+{round(row['change'],2)}%)")
                        
                        if row['is_trap']: st.error("⚠️ STATUS: TRAP DETECTED (Hati-hati Pucuk)")
                        else: st.success("✅ STATUS: CLEAN ACCUMULATION (Siap Gas)")
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Harga", f"{int(row['close'])}")
                        c2.metric("SMC Support", f"{int(poc)}")
                        c3.metric("Vol Ratio", f"{round(row['vol_ratio'],1)}x")
                        
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Grafik tidak tersedia untuk saham ini.")
                        
                        # Data untuk Telegram
                        if not row['is_trap']:
                            pesan_tele += f"{medali} <b>{saham}</b>\nHarga: {int(row['close'])}\nNaik: {round(row['change'],2)}%\nSMC Support: {int(poc)}\n\n"
                        
                        st.divider()
                
                if aktifkan_tele: kirim_telegram(pesan_tele)
            else:
                st.info("Tidak ada saham yang menembus filter ketat saat ini.")
        else:
            st.info("Pasar sedang sepi, belum ada sinyal.")
            
    except Exception as e:
        st.error(f"Terjadi kendala teknis: {e}")

# --- TIMER ---
if mode_auto:
    t_minus = st.empty()
    for s in range(900, 0, -1):
        m, sec = divmod(s, 60)
        t_minus.markdown(f"### ⏳ Next Scan: {m:02d}:{sec:02d}")
        time.sleep(1)
    st.rerun()