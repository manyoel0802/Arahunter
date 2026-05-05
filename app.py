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

st.set_page_config(page_title="GOD MODE V21.0", layout="wide", page_icon="📈")

# --- SECURITY & SECRETS ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- DATABASE WATCHLIST ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Target', 'Status'])

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-opti { background: linear-gradient(135deg, #1e1b4b 0%, #1e3a8a 100%); border-top: 5px solid #3b82f6; }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- OPTIMIZER MODULE: ATR CALCULATION ---
def calculate_atr_metrics(df, n=14):
    try:
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(n).mean().iloc[-1]
        
        last_price = df['Close'].iloc[-1]
        # Volatility Factor (Berapa % pergerakan harian rata-rata)
        vol_factor = (atr / last_price) * 100
        return round(atr, 2), round(vol_factor, 2)
    except:
        return 0, 0

# --- SENTINEL MODULE ---
def check_profit_targets():
    if st.session_state['history_log'].empty: return
    df = st.session_state['history_log']
    for index, row in df.iterrows():
        if row['Status'] == 'OPEN':
            try:
                t = yf.Ticker(f"{row['Ticker']}.JK")
                cp = t.fast_info['last_price']
                if cp >= row['Target']:
                    msg = f"🎯 <b>OPTIMIZED TARGET HIT!</b>\nStock: <b>{row['Ticker']}</b>\nPrice: {int(cp)}\n\n<i>Cuan diamankan otomatis oleh Sentinel V21.</i>"
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": msg, "parse_mode": "HTML"})
                    st.session_state['history_log'].at[index, 'Status'] = 'HIT'
            except: continue

# --- UI HEADER ---
st.markdown(f"""
    <div class='status-card bg-opti'>
        <h1 style='margin:0;'>📈 GOD MODE V21.0: OPTIMIZER</h1>
        <p style='margin:0; opacity:0.8;'>Volatility-Adjusted Targets | ATR Intel | Sentinel Active</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Optimization Settings")
    atr_multiplier = st.slider("ATR Multiplier (Risk)", 1.5, 3.0, 2.0, help="Semakin besar, semakin jauh Stop Loss (cocok untuk saham lincah).")
    rr_ratio = st.slider("Reward Ratio", 1.5, 4.0, 2.5, help="Target profit adalah X kali lipat dari risiko Stop Loss.")
    
    st.divider()
    mode = st.radio("Radar Focus:", ["Blue Chip", "Small Cap"])
    capital = st.number_input("Modal Trading (Rp)", value=2000000)
    
    if st.button("🧹 Clear Watchlist"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Target', 'Status'])
        st.rerun()

# --- MASTER SCAN ---
if st.button("🚀 EXECUTE OPTIMIZED SCAN", use_container_width=True, type="primary"):
    with st.status("Calculating Volatility & Finding Gaps...", expanded=True) as status:
        try:
            check_profit_targets()
            min_cap = 5e11 if "Blue" in mode else 5e10
            max_price = 100000 if "Blue" in mode else 500
            
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 1.5, Column('close') <= max_price))
            
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= min_cap) & (df_raw['v_ratio'] >= 1.2)]
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                for idx, row in df_scan.iterrows():
                    s_obj = yf.Ticker(f"{row['name']}.JK")
                    df_hist = s_obj.history(period="1y")
                    
                    if not df_hist.empty:
                        atr_val, vol_pct = calculate_atr_metrics(df_hist)
                        lp = float(row['close'])
                        
                        # --- DYNAMIC RISK-REWARD CALCULATION ---
                        # SL = Harga - (ATR * Multiplier)
                        # TP = Harga + ((Harga - SL) * RR Ratio)
                        sl_dist = atr_val * atr_multiplier
                        sl_final = int(lp - sl_dist)
                        tp_final = int(lp + (sl_dist * rr_ratio))
                        
                        # Update Watchlist
                        if row['name'] not in st.session_state['history_log']['Ticker'].values:
                            new_h = pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(lp), tp_final, 'OPEN']], 
                                                columns=['Waktu', 'Ticker', 'Entry', 'Target', 'Status'])
                            st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_h], ignore_index=True)
                        
                        # UI Card
                        st.markdown(f"""<div class='stock-card'>
                                <h2 style='margin:0;'>{row['name']} <span style='color:#3fb950; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='margin:0;'>📊 Volatility: <b>{vol_pct}%</b> | ATR: <b>{atr_val}</b></p>
                                </div>""", unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("ENTRY", int(lp))
                        c2.metric("OPTI-TARGET", tp_final, f"+{round(((tp_final-lp)/lp)*100,1)}%")
                        c3.metric("OPTI-STOPLOSS", sl_final, f"{round(((sl_final-lp)/lp)*100,1)}%")
                        
                        # Lot Calculation
                        risk_rp = (lp - sl_final) * 100 # Risiko per 1 lot
                        max_risk_allowed = capital * 0.02 # Pakai risk 2% modal
                        lot = int(max_risk_allowed / risk_rp) if risk_rp > 0 else 0
                        
                        st.info(f"💼 Execution: **Beli {lot} Lot** (Risk disesuaikan dengan nafas saham)")

                status.update(label="Optimization Scan Complete!", state="complete", expanded=False)
        except Exception as e: st.error(f"Error: {e}")