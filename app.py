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

st.set_page_config(page_title="GOD MODE V18.0", layout="wide", page_icon="🔱")

# --- SECURITY ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 10px; }
    .status-card { border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #30363d; color: white; }
    .bg-bull { background: linear-gradient(135deg, #064e3b 0%, #1e293b 100%); }
    .bg-bear { background: linear-gradient(135deg, #7f1d1d 0%, #1e293b 100%); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-top: 15px; border-left: 5px solid #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE HISTORY ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Mode', 'Tape'])

# --- ENGINES ---
def get_market_breadth():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="2mo")
        curr = ihsg['Close'].iloc[-1]
        ma20 = ihsg['Close'].rolling(20).mean().iloc[-1]
        return (curr > ma20), round(((curr-ma20)/ma20)*100, 2)
    except: return True, 0

def get_tape_reading(df, v_ratio):
    try:
        body = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
        range_tot = abs(df['High'].iloc[-1] - df['Low'].iloc[-1]) or 0.01
        strength = (body / range_tot) * v_ratio
        if strength > 2.2: return "BIG MONEY FLOW", "🔥"
        if strength > 1.2: return "ACCUMULATION", "✅"
        return "NORMAL FLOW", "⚖️"
    except: return "NORMAL", "⚖️"

def analyze_sentiment(news):
    if not news: return "NEUTRAL", "⚪"
    pos = ['laba', 'naik', 'untung', 'kontrak', 'ekspansi', 'akuisisi', 'positif']
    neg = ['rugi', 'turun', 'anjlok', 'kasus', 'negatif', 'sanksi']
    score = 0
    for n in news:
        txt = n.get('title', '').lower()
        score += sum(1 for w in pos if w in txt)
        score -= sum(1 for w in neg if w in txt)
    return ("BULLISH", "🟢") if score > 0 else ("BEARISH", "🔴") if score < 0 else ("NEUTRAL", "⚪")

# --- UI HEADER ---
is_bull, mkt_diff = get_market_breadth()
header_class = "bg-bull" if is_bull else "bg-bear"
st.markdown(f"<div class='status-card {header_class}'><h1 style='margin:0;'>🔱 GOD MODE V18.0</h1><p style='margin:0;'>Market: <b>{'BULLISH' if is_bull else 'BEARISH'}</b> | Global Risk Check: {'OK' if is_bull else 'CAUTION'}</p></div>", unsafe_allow_html=True)

# --- SIDEBAR (POINT PENTING: SELECTION MODE) ---
with st.sidebar:
    st.header("🎯 Radar Strategy")
    radar_mode = st.radio("Pilih Fokus Radar:", 
                          ["Blue Chip (Market Cap > 500B)", "Small Cap (Market Cap < 500B)"],
                          help="Small Cap cocok untuk modal terbatas namun risiko lebih tinggi.")
    
    st.divider()
    st.header("⚙️ Config")
    capital = st.number_input("Modal Trading (Rp)", value=2000000, step=500000)
    risk_pct = st.slider("Risk Per Trade (%)", 1, 5, 2)
    
    if st.button("🧹 Clear History"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Mode', 'Tape'])
        st.rerun()

    st.write("**Recent Signals:**")
    st.dataframe(st.session_state['history_log'].tail(10), use_container_width=True)

# --- SCANNER LOGIC ---
if st.button("🚀 EXECUTE RADAR SCAN", use_container_width=True, type="primary"):
    with st.status(f"Scanning for {radar_mode}...", expanded=True) as status:
        try:
            # Setting Parameter berdasarkan Pilihan User
            if "Blue Chip" in radar_mode:
                min_cap = 5e11 # 500 Miliar
                max_price = 100000
            else:
                min_cap = 5e10 # 50 Miliar (Menangkap saham ENZO dkk)
                max_price = 500 # Fokus saham murah di bawah Rp 500 agar lot dapat banyak
            
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 1.5, Column('close') <= max_price))
            
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                
                # Filter Market Cap & Trend
                if "Blue Chip" in radar_mode:
                    df_scan = df_raw[(df_raw['market_cap_basic'] >= min_cap) & (df_raw['v_ratio'] >= 1.5)]
                else:
                    # Filter untuk Small Cap: Lebih longgar tapi tetap cari yang ada volume
                    df_scan = df_raw[(df_raw['market_cap_basic'] < 5e11) & (df_raw['market_cap_basic'] >= min_cap) & (df_raw['v_ratio'] >= 1.2)]
                
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                if not df_scan.empty:
                    pesan_tele = f"🔱 <b>V18.0 REPORT: {radar_mode}</b>\n"
                    
                    for idx, row in df_scan.iterrows():
                        s_obj = yf.Ticker(f"{row['name']}.JK")
                        df_hist = s_obj.history(period="1y")
                        
                        if not df_hist.empty:
                            tape_label, tape_icon = get_tape_reading(df_hist, row['v_ratio'])
                            try: news = s_obj.news
                            except: news = []
                            ai_label, ai_icon = analyze_sentiment(news)
                            
                            # Log History
                            new_data = pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(row['close']), radar_mode.split()[0], tape_label]], 
                                                   columns=['Waktu', 'Ticker', 'Harga', 'Mode', 'Tape'])
                            st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_data], ignore_index=True)
                            
                            # UI Card
                            st.markdown(f"""<div class='stock-card'>
                                <h2 style='margin:0;'>{row['name']} <span style='color:#3fb950; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='margin:0;'>{tape_icon} <b>{tape_label}</b> | {ai_icon} AI: {ai_label}</p>
                                </div>""", unsafe_allow_html=True)
                            
                            t1, t2 = st.tabs(["🎯 Plan", "📉 Analysis"])
                            with t1:
                                lp = float(row['close'])
                                sl, tp = int(lp * 0.96), int(lp * 1.12)
                                c1, c2, c3 = st.columns(3)
                                c1.metric("ENTRY", int(lp))
                                c2.metric("TARGET", tp)
                                c3.metric("SL", sl)
                                
                                diff = lp - sl
                                lot = int(((capital * (risk_pct/100)) / diff) / 100) if diff > 0 else 0
                                st.info(f"💼 Strategi: **Beli {lot} Lot**")
                                if "Small Cap" in radar_mode:
                                    st.warning("⚠️ High Volatility: Saham ini lincah, pastikan disiplin SL!")
                                    
                            with t2:
                                df_p = df_hist.tail(40)
                                fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'])])
                                fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=250, xaxis_rangeslider_visible=False, template="plotly_dark")
                                st.plotly_chart(fig, use_container_width=True, key=f"c_{row['name']}")
                            
                            pesan_tele += f"\n💎 <b>{row['name']}</b> ({radar_mode.split()[0]})\nFlow: {tape_label}\nPlan: {int(lp)} -> TP {tp}\n"
                    
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                    status.update(label="Scan Complete!", state="complete", expanded=False)
                else: st.warning(f"Tidak ada saham {radar_mode} yang menarik saat ini.")
            else: st.info("Pasar sedang sideways.")
        except Exception as e: st.error(f"Error: {e}")