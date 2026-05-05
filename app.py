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

st.set_page_config(
    page_title="GOD MODE V15.5", 
    layout="centered", 
    page_icon="🦅"
)

# --- KREDENSIAL ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
TELE_CHAT_ID = "5916986433"

# --- CUSTOM UI CSS ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .report-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        border-top: 4px solid #58a6ff;
    }
    .badge-pro { padding: 3px 12px; border-radius: 12px; font-size: 11px; font-weight: bold; color: white; }
    .bg-inst { background-color: #1f6feb; }
    .bg-accum { background-color: #238636; }
    .bg-neu { background-color: #6e7681; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE HISTORY (Point 3 dari V13) ---
if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Bandar Flow', 'AI'])

# --- ENGINE ANALYTICS ---
def calculate_bandar_confidence(df, v_ratio):
    try:
        if df.empty: return 50, "DATA EMPTY", "bg-neu"
        close, low, high = df['Close'].iloc[-1], df['Low'].iloc[-1], df['High'].iloc[-1]
        ad_strength = ((close - low) - (high - close)) / (high - low) if (high - low) != 0 else 0
        v_safe = v_ratio if not np.isnan(v_ratio) else 1.0
        score = 50 + (ad_strength * 20) + (v_safe * 5)
        if np.isnan(score): score = 50
        if score > 85: return min(score, 100), "ULTRA ACCUM", "bg-accum"
        if score > 65: return score, "BIG MONEY", "bg-inst"
        return score, "NORMAL", "bg-neu"
    except: return 50, "N/A", "bg-neu"

def analyze_sentiment_pro(ticker_obj):
    try:
        news = ticker_obj.news
        if not news: return "NEUTRAL"
        pos = ['laba', 'naik', 'positif', 'kontrak', 'ekspansi', 'dividen', 'akuisisi']
        neg = ['rugi', 'turun', 'negatif', 'kasus', 'sanksi']
        score = 0
        for n in news:
            text = n['title'].lower()
            score += sum(1 for w in pos if w in text)
            score -= sum(1 for w in neg if w in text)
        return "BULLISH" if score > 0 else "BEARISH" if score < 0 else "NEUTRAL"
    except: return "NEUTRAL"

# --- UI APP ---
st.title("🦅 GOD MODE V15.5")
st.caption("Institutional Intelligence + History Tracker | Stable Build")

with st.sidebar:
    st.header("📋 History Radar")
    if not st.session_state['history'].empty:
        st.dataframe(st.session_state['history'].tail(15), use_container_width=True)
        if st.button("🧹 Reset Log"):
            st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Bandar Flow', 'AI'])
            st.rerun()
    else:
        st.info("Scan belum dijalankan.")
    st.divider()
    st.header("⚙️ Konfigurasi")
    capital = st.number_input("Modal (Rp)", value=10000000, step=1000000)
    risk_val = st.slider("Risiko Per Trade (%)", 1, 5, 2)
    st.divider()
    manual_tele = st.toggle("Sync Telegram", value=True)

# --- MASTER SCAN ---
if st.button("🚀 INITIATE MASTER RADAR", use_container_width=True, type="primary"):
    with st.status("Reading BEI Money Flow...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia').select('name','close','change', 'open', 'high', 'low', 'volume','average_volume_10d_calc','SMA50','market_cap_basic')
                 .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 5e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                if not df_scan.empty:
                    pesan_tele = f"🦅 <b>V15.5 MASTER REPORT</b>\n"
                    for idx, row in df_scan.iterrows():
                        s_obj = yf.Ticker(f"{row['name']}.JK")
                        df_hist = s_obj.history(period="1y")
                        
                        if not df_hist.empty:
                            b_score, b_label, b_class = calculate_bandar_confidence(df_hist, row['v_ratio'])
                            s_label = analyze_sentiment_pro(s_obj)
                            
                            last_p = float(row['close'])
                            sl, tp = int(last_p * 0.96), int(last_p * 1.12)
                            
                            # --- UPDATE HISTORY LOG ---
                            new_log = pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(last_p), b_label, s_label]], 
                                                  columns=['Waktu', 'Ticker', 'Harga', 'Bandar Flow', 'AI'])
                            st.session_state['history'] = pd.concat([st.session_state['history'], new_log], ignore_index=True)
                            
                            # UI Card
                            st.markdown(f"""
                                <div class='report-card'>
                                    <h2 style='margin:0;'>{row['name']} <span style='color:#3fb950;'>+{round(row['change'],2)}%</span></h2>
                                    <span class='badge-pro {b_class}'>{b_label}</span> 
                                    <span class='badge-pro bg-inst' style='margin-left:5px;'>AI: {s_label}</span>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            t1, t2 = st.tabs(["📝 Plan", "📊 Analysis"])
                            with t1:
                                c1, c2, c3 = st.columns(3)
                                c1.metric("ENTRY", int(last_p))
                                c2.metric("TARGET", tp)
                                c3.metric("STOP LOSS", sl)
                                diff = last_p - sl
                                lot = int(((capital * (risk_val/100)) / diff) / 100) if diff > 0 else 0
                                st.success(f"💼 **Action:** Buy **{lot} Lots**")
                                
                            with t2:
                                val_gauge = b_score if not np.isnan(b_score) else 50
                                fig = go.Figure(go.Indicator(mode="gauge+number", value=val_gauge, title={'text': "Bandar Confidence", 'font': {'size': 14}}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#58a6ff"}}))
                                fig.update_layout(height=180, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor='rgba(0,0,0,0)')
                                st.plotly_chart(fig, use_container_width=True, key=f"g_{row['name']}")
                            
                            pesan_tele += f"\n🔥 <b>{row['name']}</b>\nFlow: {b_label}\nTP: {tp} | SL: {sl}\n"
                    
                    if manual_tele:
                        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                    status.update(label="Scanning Success!", state="complete", expanded=False)
                else: st.warning("No high confidence signals.")
            else: st.info("Market is sideways.")
        except Exception as e: st.error(f"Error: {e}")