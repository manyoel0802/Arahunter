import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import requests
import warnings
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI SISTEM ---
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V20.0", layout="wide", page_icon="🏦")

# --- SECURITY & SECRETS ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- DATABASE HISTORY (Ditingkatkan untuk Menyimpan Target) ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Target', 'Status'])

# --- UI CUSTOM STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-sentinel { background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-top: 5px solid #6366f1; }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- SENTINEL MODULE: PROFIT CHECKER ---
def check_profit_targets():
    if st.session_state['history_log'].empty:
        return "History kosong. Belum ada target untuk dipantau."
    
    hits = []
    df = st.session_state['history_log']
    
    with st.spinner("Checking profit targets in real-time..."):
        for index, row in df.iterrows():
            if row['Status'] == 'OPEN':
                try:
                    # Ambil harga terbaru
                    ticker = yf.Ticker(f"{row['Ticker']}.JK")
                    current_price = ticker.fast_info['last_price']
                    
                    if current_price >= row['Target']:
                        # Kirim Alert Telegram
                        msg = f"🎯 <b>PROFIT TARGET HIT!</b>\n\nStock: <b>{row['Ticker']}</b>\nCurrent: {int(current_price)}\nTarget: {int(row['Target'])}\n\n<i>Silakan lakukan Take Profit sesuai rencana.</i>"
                        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", 
                                      data={"chat_id": TELE_CHAT_ID, "text": msg, "parse_mode": "HTML"})
                        
                        # Update Status di Database Lokal
                        st.session_state['history_log'].at[index, 'Status'] = 'HIT'
                        hits.append(row['Ticker'])
                except:
                    continue
    
    if hits:
        return f"Berhasil! Target {', '.join(hits)} telah tercapai dan notifikasi dikirim."
    return "Belum ada target baru yang tersentuh saat ini."

# --- ENGINES ---
def get_ihsg_context():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="2mo")
        curr = ihsg['Close'].iloc[-1]
        ma20 = ihsg['Close'].rolling(20).mean().iloc[-1]
        return (curr > ma20), round(((curr-ma20)/ma20)*100, 2)
    except: return True, 0

def get_tape_logic(df, v_ratio):
    try:
        body = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
        range_tot = abs(df['High'].iloc[-1] - df['Low'].iloc[-1]) or 0.01
        strength = (body / range_tot) * v_ratio
        if strength > 2.2: return "BIG FISH ENTRY", "🔥"
        if strength > 1.3: return "ACCUMULATION", "✅"
        return "NORMAL FLOW", "⚖️"
    except: return "NORMAL", "⚖️"

# --- UI HEADER ---
is_safe, mkt_diff = get_ihsg_context()
st.markdown(f"""
    <div class='status-card bg-sentinel'>
        <h1 style='margin:0;'>🏦 GOD MODE V20.0: PROFIT SENTINEL</h1>
        <p style='margin:0; opacity:0.8;'>Market Strength: <b>{mkt_diff}%</b> | Sentinel Status: <b>ACTIVE</b></p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("🛡️ Sentinel Command")
    if st.button("🎯 CHECK PROFIT TARGETS NOW", use_container_width=True, type="secondary"):
        result = check_profit_targets()
        st.toast(result)
    
    st.divider()
    st.header("🎯 Strategy Selector")
    mode = st.radio("Radar Focus:", ["Blue Chip (Stable)", "Small Cap (Aggressive)"])
    st.divider()
    st.header("⚙️ Capital Control")
    capital = st.number_input("Modal (Rp)", value=2000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1, 5, 2)
    
    st.divider()
    st.write("**Active Watchlist:**")
    st.dataframe(st.session_state['history_log'], use_container_width=True)
    if st.button("🧹 Clear Watchlist"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Target', 'Status'])
        st.rerun()

# --- MASTER EXECUTION ---
if st.button("🚀 RUN SENTINEL SCANNER", use_container_width=True, type="primary"):
    with st.status("Analyzing Market Flow & Targets...", expanded=True) as status:
        try:
            # Otomatis cek profit di awal scan
            check_profit_targets()
            
            min_cap = 5e11 if "Blue" in mode else 5e10
            max_price = 100000 if "Blue" in mode else 500
            
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 1.5, Column('close') <= max_price))
            
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= min_cap) & (df_raw['v_ratio'] >= 1.2)]
                
                if "Small" in mode:
                    df_scan = df_scan[df_raw['market_cap_basic'] < 5e11]
                
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                for idx, row in df_scan.iterrows():
                    s_obj = yf.Ticker(f"{row['name']}.JK")
                    df_hist = s_obj.history(period="1y")
                    
                    if not df_hist.empty:
                        tape_label, tape_icon = get_tape_logic(df_hist, row['v_ratio'])
                        lp = float(row['close'])
                        sl, tp = int(lp * 0.96), int(lp * 1.12)
                        
                        # Simpan ke Watchlist dengan status OPEN
                        if row['name'] not in st.session_state['history_log']['Ticker'].values:
                            new_h = pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(lp), int(tp), 'OPEN']], 
                                                columns=['Waktu', 'Ticker', 'Entry', 'Target', 'Status'])
                            st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_h], ignore_index=True)
                        
                        # UI Card
                        st.markdown(f"""<div class='stock-card'>
                                <h2 style='margin:0;'>{row['name']} <span style='color:#3fb950; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='margin:0;'>{tape_icon} <b>{tape_label}</b> | Target Take Profit: <b>Rp {tp}</b></p>
                                </div>""", unsafe_allow_html=True)
                        
                        # Lot Sizing Formula
                        # $$Lot = \frac{Capital \times Risk\%}{Entry - SL} \div 100$$
                        diff = lp - sl
                        lot = int(((capital * (risk_pct/100)) / diff) / 100) if diff > 0 else 0
                        if not is_safe: lot = int(lot/2)
                        st.info(f"💼 Strategi: **Beli {lot} Lot**")

                status.update(label="Sentinel Scan Complete!", state="complete", expanded=False)
            else: st.warning("Belum ada sinyal yang memenuhi kriteria.")
        except Exception as e: st.error(f"Error: {e}")