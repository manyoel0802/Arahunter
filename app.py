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

st.set_page_config(page_title="GOD MODE V17.0", layout="wide", page_icon="🔱")

# --- SECURITY & SECRETS ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- UI CUSTOM STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 10px; }
    .status-card { border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #30363d; color: white; }
    .bg-bull { background: linear-gradient(135deg, #064e3b 0%, #1e293b 100%); }
    .bg-bear { background: linear-gradient(135deg, #7f1d1d 0%, #1e293b 100%); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE HISTORY (V13) ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Tape', 'Sentiment'])

# --- MARKET BREADTH ENGINE (V16) ---
def get_market_breadth():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="2mo")
        curr = ihsg['Close'].iloc[-1]
        ma20 = ihsg['Close'].rolling(20).mean().iloc[-1]
        is_safe = curr > ma20
        return is_safe, round(((curr-ma20)/ma20)*100, 2)
    except: return True, 0

# --- TAPE READING PROXY (V13 - Classic) ---
def get_tape_reading(df, v_ratio):
    try:
        body = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
        range_tot = abs(df['High'].iloc[-1] - df['Low'].iloc[-1])
        range_tot = range_tot if range_tot != 0 else 0.01
        strength = (body / range_tot) * v_ratio
        if strength > 2.2: return "BIG FISH ENTRY", "🔥"
        if strength > 1.3: return "ACCUMULATION", "✅"
        return "NORMAL FLOW", "⚖️"
    except: return "NORMAL", "⚖️"

# --- AI SENTIMENT ENGINE (V13 - Keyword Based) ---
def analyze_sentiment_classic(news):
    if not news: return "NEUTRAL", "⚪"
    pos = ['laba', 'naik', 'untung', 'kontrak', 'ekspansi', 'dividen', 'akuisisi', 'rekor', 'positif']
    neg = ['rugi', 'turun', 'anjlok', 'kasus', 'negatif', 'sanksi', 'suspensi']
    score = 0
    for n in news:
        txt = n['title'].lower()
        score += sum(1 for w in pos if w in txt)
        score -= sum(1 for w in neg if w in txt)
    if score > 0: return "BULLISH", "🟢"
    if score < 0: return "BEARISH", "🔴"
    return "NEUTRAL", "⚪"

# --- FUNDAMENTAL & POC (V16 & V12) ---
def get_advanced_metrics(s_obj, df):
    try:
        # Fundamental (V16)
        info = s_obj.info
        npm = info.get('profitMargins', 0) or 0
        der = (info.get('debtToEquity', 0) or 0) / 100
        # POC Calculation (V12)
        df['Price_Bin'] = df['Close'].round(-1)
        poc = df.groupby('Price_Bin')['Volume'].sum().idxmax()
        return npm, der, poc
    except: return 0, 0, df['Close'].mean()

# --- UI HEADER ---
is_bull, mkt_diff = get_market_breadth()
header_class = "bg-bull" if is_bull else "bg-bear"
st.markdown(f"""
    <div class='status-card {header_class}'>
        <h1 style='margin:0;'>🔱 GOD MODE V17.0: THE ULTIMATE</h1>
        <p style='margin:0;'>Market Status: <b>{'BULLISH (SAFE)' if is_bull else 'BEARISH (RISK)'}</b> ({mkt_diff}% from MA20)</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR (Classic V13 Style) ---
with st.sidebar:
    st.header("📋 Signal History")
    st.dataframe(st.session_state['history_log'].tail(10), use_container_width=True)
    if st.button("Clear Log"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Tape', 'Sentiment'])
        st.rerun()
    st.divider()
    capital = st.number_input("Modal Trading (Rp)", value=10000000)
    risk_pct = st.slider("Risiko Per Saham (%)", 1, 5, 2)
    strict_mode = st.toggle("Strict Filter (Profit Only)", value=False)

# --- SCANNER EXECUTION ---
if st.button("🚀 INITIATE ULTIMATE SCAN", use_container_width=True, type="primary"):
    with st.status("Merging V1-V13 Intelligence...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 5e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                pesan_tele = f"🔱 <b>V17.0 ULTIMATE REPORT</b>\n"
                
                for idx, row in df_scan.iterrows():
                    s_obj = yf.Ticker(f"{row['name']}.JK")
                    df_hist = s_obj.history(period="1y")
                    
                    if not df_hist.empty:
                        npm, der, poc = get_advanced_metrics(s_obj, df_hist)
                        if strict_mode and npm <= 0: continue
                            
                        tape_label, tape_icon = get_tape_reading(df_hist, row['v_ratio'])
                        ai_label, ai_icon = analyze_sentiment_classic(s_obj.news)
                        
                        # Save to History
                        new_log = pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(row['close']), tape_label, ai_label]], 
                                              columns=['Waktu', 'Ticker', 'Harga', 'Tape', 'Sentiment'])
                        st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_log], ignore_index=True)
                        
                        # UI Card
                        st.markdown(f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{row['name']} <span style='color:#3fb950; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='margin-bottom:10px;'>{tape_icon} <b>{tape_label}</b> | {ai_icon} <b>AI: {ai_label}</b></p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        t1, t2, t3 = st.tabs(["🎯 Strategy Plan", "📉 Chart Analysis", "📰 Live News"])
                        
                        with t1:
                            c1, c2, c3 = st.columns(3)
                            last_p = float(row['close'])
                            sl, tp = int(last_p * 0.96), int(last_p * 1.12)
                            c1.metric("ENTRY", int(last_p))
                            c2.metric("TARGET (12%)", tp)
                            c3.metric("STOP LOSS (4%)", sl)
                            
                            diff = last_p - sl
                            lot = int(((capital * (risk_pct/100)) / diff) / 100) if diff > 0 else 0
                            if not is_bull: lot = int(lot/2)
                            st.info(f"💼 Action: **Buy {lot} Lot** {'(Reduced due to Market Risk)' if not is_bull else ''}")
                            
                        with t2:
                            df_p = df_hist.tail(45)
                            fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'])])
                            # POC Line dari V12
                            fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="cyan", width=2, dash="dot"), name="POC"))
                            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_{row['name']}")
                            
                        with t3:
                            for n in s_obj.news[:3]:
                                st.markdown(f"• **{n['title']}** <br><small>{n['publisher']} | [Read Article]({n['link']})</small>", unsafe_allow_html=True)
                        
                        pesan_tele += f"\n💎 <b>{row['name']}</b>\nFlow: {tape_icon} {tape_label}\nAI: {ai_icon} {ai_label}\nPlan: {int(last_p)} -> TP {tp}\n"
                
                requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                status.update(label="V17.0 Ultimate Scan Complete!", state="complete", expanded=False)
        except Exception as e: st.error(f"Engine Error: {e}")