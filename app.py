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

st.set_page_config(page_title="GOD MODE V16.1", layout="wide", page_icon="🏦")

# --- POINT 5: SECRETS MANAGEMENT ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    # Fallback jika belum setting secrets (untuk testing)
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- CUSTOM UI ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 10px; }
    .status-card { border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #30363d; }
    .bg-safe { background: linear-gradient(135deg, #1e293b 0%, #064e3b 100%); }
    .bg-risk { background: linear-gradient(135deg, #1e293b 0%, #7f1d1d 100%); }
    </style>
    """, unsafe_allow_html=True)

# --- POINT 2: MARKET BREADTH ---
def get_ihsg_status():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="2mo")
        if ihsg.empty: return "UNKNOWN", "bg-neu", 0
        current = ihsg['Close'].iloc[-1]
        ma20 = ihsg['Close'].rolling(20).mean().iloc[-1]
        status = "BULLISH (SAFE)" if current > ma20 else "BEARISH (RISK)"
        color = "bg-safe" if current > ma20 else "bg-risk"
        return status, color, round(((current-ma20)/ma20)*100, 2)
    except: return "UNKNOWN", "bg-neu", 0

# --- POINT 1: FUNDAMENTAL HEALTH (Fixed for NaN) ---
def check_fundamental(ticker_obj):
    try:
        info = ticker_obj.info
        # Gunakan np.nan_to_num untuk merubah NaN menjadi 0
        npm = info.get('profitMargins')
        npm = float(npm) if npm is not None and not np.isnan(float(npm)) else 0.0
        
        der = info.get('debtToEquity')
        der = float(der) / 100 if der is not None and not np.isnan(float(der)) else 0.0
        
        # Anggap lolos jika NPM > 0 (Profit) dan DER < 2 (Hutang sehat)
        # Jika data tidak ada (0.0), kita anggap lolos agar tidak terlalu ketat
        is_healthy = (npm >= 0 and der <= 2.0)
        return is_healthy, npm, der
    except: 
        return True, 0.0, 0.0

# --- POINT 4: PERFORMANCE TRACKER ---
def calculate_win_rate():
    if 'history_log' not in st.session_state or not st.session_state['history_log']:
        return 0, 0
    df_h = pd.DataFrame(st.session_state['history_log'])
    wins = len(df_h[df_h['Flow'] == "ULTRA ACCUM"])
    rate = (wins / len(df_h)) * 100 if len(df_h) > 0 else 0
    return round(rate, 1), len(df_h)

# --- ANALYTICS ENGINE ---
def calculate_advanced_flow(df, v_ratio):
    try:
        close, low, high = df['Close'].iloc[-1], df['Low'].iloc[-1], df['High'].iloc[-1]
        ad_strength = ((close - low) - (high - close)) / (high - low) if (high - low) != 0 else 0
        v_safe = float(v_ratio) if not np.isnan(v_ratio) else 1.0
        score = 50 + (ad_strength * 25) + (v_safe * 5)
        if np.isnan(score): score = 50
        
        if score > 85: return min(score, 100), "ULTRA ACCUM"
        if score > 65: return score, "BIG MONEY"
        return score, "NORMAL"
    except: return 50, "N/A"

# --- UI APP ---
if 'history_log' not in st.session_state: st.session_state['history_log'] = []

ihsg_label, ihsg_color, ihsg_diff = get_ihsg_status()
st.markdown(f"""
    <div class='status-card {ihsg_color}'>
        <h1 style='margin:0; color:white;'>🦅 GOD MODE V16.1</h1>
        <p style='margin:0; color:#e2e8f0;'>IHSG Status: <b>{ihsg_label}</b> ({ihsg_diff}% vs MA20) | {datetime.now().strftime('%H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("📈 Strategy Performance")
    win_rate, total_signals = calculate_win_rate()
    st.metric("Win Rate (Est.)", f"{win_rate}%", f"{total_signals} Signals")
    st.divider()
    capital = st.number_input("Modal (Rp)", value=10000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1, 5, 2)
    strict_mode = st.toggle("Strict Fundamental Filter", value=False) # Matikan default agar tidak terlalu ketat
    if st.button("🗑️ Reset Database"):
        st.session_state['history_log'] = []
        st.rerun()

if st.button("🚀 EXECUTE ALPHA SCAN", use_container_width=True, type="primary"):
    with st.status("Engines Online: Processing Data Flows...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 5e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                pesan_tele = f"🏦 <b>V16.1 ALPHA REPORT</b>\nMarket: {ihsg_label}\n"
                
                for idx, row in df_scan.iterrows():
                    s_obj = yf.Ticker(f"{row['name']}.JK")
                    is_healthy, npm, der = check_fundamental(s_obj)
                    
                    if strict_mode and not is_healthy: continue
                        
                    df_hist = s_obj.history(period="1y")
                    if not df_hist.empty:
                        b_score, b_label = calculate_advanced_flow(df_hist, row['v_ratio'])
                        
                        last_p = float(row['close']) if not np.isnan(row['close']) else 0.0
                        if last_p == 0: continue
                            
                        sl, tp = int(last_p * 0.96), int(last_p * 1.12)
                        st.session_state['history_log'].append({'Ticker': row['name'], 'Flow': b_label})
                        
                        with st.container():
                            st.subheader(f"{idx+1}. {row['name']} (+{round(row['change'],2)}%)")
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("FLOW SCORE", f"{int(b_score)}%", b_label)
                            c2.metric("NPM", f"{round(npm*100,1)}%")
                            c3.metric("DER", f"{round(der,2)}x")
                            c4.metric("TARGET", f"Rp {tp}")
                            
                            t1, t2 = st.tabs(["🎯 Execution", "📊 Flow Analytics"])
                            with t1:
                                risk_rp = capital * (risk_pct/100)
                                diff = last_p - sl
                                lot = int((risk_rp / diff) / 100) if diff > 0 else 0
                                if ihsg_label == "BEARISH (RISK)":
                                    st.error(f"⚠️ MARKET RISK: Batasi ke **{int(lot/2)} Lot**")
                                else:
                                    st.success(f"✅ MARKET SAFE: Sikat **{lot} Lot**")
                            with t2:
                                fig = go.Figure(go.Indicator(mode="gauge+number", value=b_score, gauge={'axis':{'range':[0,100]}}))
                                fig.update_layout(height=180, margin=dict(l=10,r=10,t=30,b=10), paper_bgcolor='rgba(0,0,0,0)')
                                st.plotly_chart(fig, use_container_width=True, key=f"g_{row['name']}")
                            
                            pesan_tele += f"\n💎 <b>{row['name']}</b>\nFlow: {b_label} | NPM: {round(npm*100,1)}%\nPlan: {int(last_p)} -> TP {tp}\n"
                
                requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                status.update(label="Scan Complete!", state="complete", expanded=False)
            else: st.info("Pasar sedang sideways.")
        except Exception as e: st.error(f"Engine Error: {e}")