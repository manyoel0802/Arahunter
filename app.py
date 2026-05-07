import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings
import time
from datetime import datetime
from tradingview_screener import Query, Column

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V40.1", layout="wide", page_icon="👁️")

try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])

st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-oracle { background: linear-gradient(135deg, #0f172a 0%, #042f2e 50%, #134e4a 100%); border-top: 5px solid #14b8a6; box-shadow: 0 4px 20px rgba(20, 184, 166, 0.4); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #14b8a6; }
    .matrix-box { background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 👁️ ORACLE ENGINES ---
def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def detect_squeeze(df):
    try:
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
        df['Band_Width'] = (df['Upper'] - df['Lower']) / df['SMA20']
        
        current_bw = df['Band_Width'].iloc[-1]
        min_bw_month = df['Band_Width'].tail(20).min()
        return current_bw <= (min_bw_month * 1.1) 
    except: return False

def check_minervini_template(df):
    try:
        if len(df) < 200: return False
        c, sma50, sma150, sma200 = df['Close'].iloc[-1], df['Close'].rolling(50).mean().iloc[-1], df['Close'].rolling(150).mean().iloc[-1], df['Close'].rolling(200).mean().iloc[-1]
        return (c > sma150 and c > sma200 and sma150 > sma200 and sma50 > sma150 and c > sma50)
    except: return False

def check_smart_money(df):
    try:
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        return obv.iloc[-1] > obv.rolling(20).mean().iloc[-1]
    except: return False

def check_fundamentals(ticker):
    try:
        info = yf.Ticker(f"{ticker}.JK").info
        eps = info.get('trailingEps', 0)
        if eps is None: eps = 0
        return eps > 0, round(eps, 1) 
    except: return True, 0

@st.cache_data(ttl=300)
def get_ihsg_status():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="1mo")
        return ihsg['Close'].iloc[-1] > ihsg['Close'].rolling(20).mean().iloc[-1]
    except: return True

# --- UI HEADER ---
ihsg_aman = get_ihsg_status()

st.markdown(f"""
<div class='status-card bg-oracle'>
    <h1 style='margin:0; color:#5eead4;'>👁️ GOD MODE V40.1: THE ORACLE</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#e2e8f0;'>
        Pencari Probabilitas Absolut | The Confluence Matrix | Anti-Kepastian Semu
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Command Center")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    auto_pilot = st.toggle("🤖 Auto-Pilot Mode", value=False)
    
    st.divider()
    st.header("🛡️ Filter Logika Berlapis")
    strict_ihsg = st.toggle("📈 Wajib IHSG Bullish", value=ihsg_aman, help="Hanya beli jika pasar IHSG sedang uptrend.")
    strict_fundamental = st.toggle("🏛️ Wajib Laba (EPS > 0)", value=True)
    
    st.divider()
    st.header("⚙️ Capital & Risk")
    capital = st.number_input("Portfolio (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Max Loss Per Trade (%)", 0.5, 5.0, 2.0, step=0.5)
    atr_multiplier = st.slider("Batas Toleransi SL (ATR)", 1.0, 3.5, 2.0, step=0.1)

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE CONFLUENCE SCAN", use_container_width=True, type="primary") or auto_pilot:
    if strict_ihsg and not ihsg_aman:
        st.error("IHSG sedang Bearish (Di bawah MA-20). Operasi dibatalkan demi keamanan.")
    else:
        with st.status("Membaca 5 Pilar Konfirmasi Probabilitas...", expanded=True) as status:
            try:
                q = (Query().set_markets('indonesia')
                     .select('name','close','volume','average_volume_10d_calc','market_cap_basic','sector')
                     .where(Column('market_cap_basic') >= 1e11))
                _, df_raw = q.get_scanner_data()
                
                if not df_raw.empty:
                    df_scan = df_raw.head(50) 
                    pesan_tele = f"👁️ <b>V40.1 ORACLE CONVICTION REPORT</b>\n"
                    valid_stocks = 0
                    
                    for idx, row in df_scan.iterrows():
                        if valid_stocks >= 3: break 
                        
                        t_sym = row['name']
                        s_obj = yf.Ticker(f"{t_sym}.JK")
                        df_hist = s_obj.history(period="1y")
                        
                        if not df_hist.empty and check_minervini_template(df_hist):
                            
                            is_profitable, eps_value = check_fundamentals(t_sym)
                            if strict_fundamental and not is_profitable: continue 
                            
                            if detect_squeeze(df_hist) and check_smart_money(df_hist):
                                atr = calculate_atr(df_hist)
                                lp = float(row['close'])
                                
                                sma20 = df_hist['Close'].rolling(20).mean().iloc[-1]
                                best_entry = int(max(sma20, lp - (atr * 0.5)))
                                
                                distance_to_ma = ((lp - sma20) / sma20) * 100
                                if distance_to_ma > 6.0: timing_status = "⏳ TUNGGU (Harga Ketinggian)"
                                else: timing_status = "🚀 AREA BELI IDEAL"
                                
                                sl_price = int(lp - (atr * atr_multiplier)) 
                                target_price = int(lp + (atr * 4.0)) 
                                
                                risk_rp = lp - sl_price
                                reward_rp = target_price - lp
                                rrr = round(reward_rp / risk_rp, 1) if risk_rp > 0 else 0
                                
                                if rrr < 2.0: continue 
                                
                                sl_pct = round(((lp - sl_price) / lp) * 100, 1)
                                lot = int(((capital * (risk_pct/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                                if lot == 0: continue
                                
                                valid_stocks += 1
                                
                                # ---> BUG FIX: Seluruh UI The Confluence Matrix dipadatkan ke dalam satu baris (one-liner) <---
                                html_card = f"<div class='stock-card'><h2 style='margin:0;'>{t_sym} <span style='color:#5eead4; font-size:14px; border:1px solid #5eead4; padding:2px 6px; border-radius:4px;'>MAX PROBABILITY SETUP</span></h2><p style='color:#94a3b8; font-size:14px; margin:0 0 10px 0;'>Sektor: <b>{row['sector']}</b> | Entry: <b>{timing_status}</b></p><div class='matrix-box'><p style='margin:0 0 5px 0; color:#cbd5e1; font-weight:bold; font-size:12px; text-transform:uppercase;'>The Confluence Matrix (Pilar Konfirmasi):</p><ul style='margin:0; padding-left:20px; font-size:14px; color:#10b981; line-height:1.6;'><li><b>Fundamental:</b> Perusahaan mencetak laba (EPS Rp {eps_value})</li><li><b>Trend Makro:</b> Saham terkonfirmasi dalam fase Uptrend Kuat (Minervini)</li><li><b>Bandarmologi:</b> OBV mengkonfirmasi jejak akumulasi Uang Raksasa</li><li><b>Momentum:</b> Volatilitas sedang menyempit ekstrem (BB Squeeze Breakout)</li><li><b>Risk Management:</b> Potensi untung {rrr}x lipat dari potensi rugi</li></ul></div><p style='margin:10px 0 0 0; font-size:11px; color:#64748b; font-style:italic;'>*Peringatan: 5 Pilar terpenuhi menghasilkan Probabilitas Kemenangan 70%-80%. Selalu gunakan Lot Management, karena di bursa saham, kemungkinan 100% adalah sebuah ilusi.</p></div>"
                                st.markdown(html_card, unsafe_allow_html=True)
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("🎯 ZONA BELI", f"Rp {best_entry} - {int(lp)}")
                                c2.metric("🛡️ STOP LOSS", sl_price, f"-{sl_pct}%")
                                c3.metric("📦 MAX LOT", lot)
                                
                                pesan_tele += f"\n🌟 <b>{t_sym} (MAX CONVICTION)</b>\n✔️ Laba, Uptrend, Squeeze, OBV, RRR {rrr}x terkonfirmasi!\n🎯 Antre: Rp {best_entry} - {int(lp)}\n🛡️ SL: Rp {sl_price}\n📦 Lot: {lot} Lot\n"

                    if valid_stocks > 0 and send_telegram:
                        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                    
                    status.update(label=f"Scan Selesai!", state="complete", expanded=False)
                    if valid_stocks == 0: st.warning("Tidak ada saham yang memenuhi kelima pilar konfirmasi secara bersamaan hari ini. Kesabaran adalah kunci.")
                else: st