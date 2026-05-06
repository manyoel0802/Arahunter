import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import requests
import warnings
import time
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI SISTEM ---
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V28.0", layout="wide", page_icon="🧠")

# --- SECURITY ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- DATABASE ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=[
        'Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'
    ])
if 'last_scan' not in st.session_state:
    st.session_state['last_scan'] = "Belum ada scan"

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-ai { background: linear-gradient(135deg, #0f172a 0%, #312e81 100%); border-top: 5px solid #06b6d4; }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; }
    .badge-pro { padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .badge-ai { padding: 4px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; background: #06b6d4; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 🧠 DEEPQUANT AI ENGINE ---
def calculate_rsi(data, periods=14):
    close_delta = data['Close'].diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    ma_up = up.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    ma_down = down.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    rsi = ma_up / ma_down
    rsi = 100 - (100/(1 + rsi))
    return rsi

def nlp_sentiment_analysis(news_data):
    if not news_data: return 50 # Netral
    pos_words = ['laba', 'naik', 'untung', 'akuisisi', 'ekspansi', 'kontrak', 'positif', 'tumbuh', 'rekor']
    neg_words = ['rugi', 'turun', 'anjlok', 'kasus', 'negatif', 'sanksi', 'gagal', 'susut', 'utang']
    score = 50
    for n in news_data:
        title = n.get('title', '').lower()
        if any(w in title for w in pos_words): score += 10
        if any(w in title for w in neg_words): score -= 10
    return max(0, min(100, score)) # Batasi 0-100

def deepquant_ai_score(df, news):
    """
    Kalkulasi Probabilitas AI menggunakan rumus hibrida (Momentum + Volatility Squeeze + Sentiment)
    """
    try:
        if len(df) < 50: return 50, "Data tidak cukup"
        
        # 1. Momentum Check (RSI)
        df['RSI'] = calculate_rsi(df)
        curr_rsi = df['RSI'].iloc[-1]
        # AI suka RSI di atas 55 tapi belum overbought ekstrim (< 80)
        rsi_score = 100 if 55 <= curr_rsi <= 75 else (curr_rsi if curr_rsi < 55 else 40)
        
        # 2. Volatility Contraction (VCP) - Bollinger Bands Squeeze
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Upper_BB'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower_BB'] = df['SMA20'] - (df['STD20'] * 2)
        bb_width = (df['Upper_BB'] - df['Lower_BB']) / df['SMA20']
        curr_bb_width = bb_width.iloc[-1]
        avg_bb_width = bb_width.rolling(20).mean().iloc[-1]
        
        # Jika BB_width saat ini lebih kecil dari rata-rata (Squeeze), AI beri nilai tinggi
        vcp_score = 100 if curr_bb_width < avg_bb_width else 40
        
        # 3. Sentiment Check
        sent_score = nlp_sentiment_analysis(news)
        
        # 🧠 AI Neural Weighting Formula:
        # $$ AI\_Score = (RSI \times 0.4) + (VCP \times 0.4) + (Sentiment \times 0.2) $$
        final_score = int((rsi_score * 0.4) + (vcp_score * 0.4) + (sent_score * 0.2))
        
        # AI Recommendation Tag
        if final_score >= 80: tag = "🔥 STRONG CONVICTION"
        elif final_score >= 65: tag = "✅ HIGH PROBABILITY"
        else: tag = "⚖️ NEUTRAL/RISKY"
        
        return final_score, tag
    except: return 50, "⚖️ ERROR/NEUTRAL"

# --- GRANDMASTER ENGINES (Dari V26) ---
@st.cache_data(ttl=300)
def get_ihsg_data():
    try: return yf.Ticker("^JKSE").history(period="3mo")
    except: return pd.DataFrame()

def check_minervini_template(df):
    try:
        if len(df) < 200: return False
        c = df['Close'].iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        sma150 = df['Close'].rolling(150).mean().iloc[-1]
        sma200 = df['Close'].rolling(200).mean().iloc[-1]
        high_52 = df['High'].rolling(252).max().iloc[-1]
        low_52 = df['Low'].rolling(252).min().iloc[-1]
        
        return (c > sma150 and c > sma200 and sma150 > sma200 and 
                sma50 > sma150 and sma50 > sma200 and c > sma50 and 
                c >= (low_52 * 1.30) and c >= (high_52 * 0.75))
    except: return False

def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), 
             np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

# --- UI HEADER ---
ihsg_df = get_ihsg_data()
ihsg_safe = ihsg_df['Close'].iloc[-1] > ihsg_df['Close'].rolling(20).mean().iloc[-1] if not ihsg_df.empty else True

st.markdown(f"""
    <div class='status-card bg-ai'>
        <h1 style='margin:0; color:#22d3ee;'>🧠 GOD MODE V28.0: AI NEXUS</h1>
        <p style='margin:0; opacity:0.8; color:#e2e8f0;'>DeepQuant AI Engine | Minervini Rules | NLP Sentiment</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR & AUTOMATION TOGGLES ---
with st.sidebar:
    st.header("🎛️ AI Engine Control")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    ai_strict_mode = st.toggle("🤖 AI Strict Mode (>70% Score)", value=True, help="Hanya beli jika AI sangat yakin (Skor > 70%).")
    
    st.divider()
    st.header("⚙️ Strategy Config")
    ts_sensitivity = st.select_slider("Sensitivitas Trailing (ATR):", options=[1.5, 2.0, 2.5, 3.0], value=2.5)
    capital = st.number_input("Portfolio Size (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1.0, 3.0, 2.0, step=0.5)
    
    st.divider()
    st.write("**📡 AI Trailing Tracker:**")
    active_portfolio = st.session_state['history_log'][st.session_state['history_log']['Status'] == 'OPEN']
    
    if not active_portfolio.empty:
        display_df = active_portfolio[['Ticker', 'Current_Price', 'Trailing_SL']].copy()
        display_df['Current_Price'] = pd.to_numeric(display_df['Current_Price'], errors='coerce')
        display_df['Trailing_SL'] = pd.to_numeric(display_df['Trailing_SL'], errors='coerce')
        display_df['Jarak SL'] = ((display_df['Current_Price'] - display_df['Trailing_SL']) / display_df['Current_Price'] * 100).round(1).astype(str) + '%'
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else: st.info("Portofolio kosong.")
        
    if st.button("🧹 Clear Portfolio"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
        st.rerun()

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE DEEPQUANT AI SCAN", use_container_width=True, type="primary"):
    with st.status("AI Neural Network is Processing Market Data...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 1.5, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 1e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(10).reset_index(drop=True)
                
                pesan_tele = f"🧠 <b>V28.0 DEEPQUANT AI REPORT</b>\n"
                valid_stocks = 0
                
                for idx, row in df_scan.iterrows():
                    if valid_stocks >= 3: break 
                    
                    t_sym = row['name']
                    s_obj = yf.Ticker(f"{t_sym}.JK")
                    df_hist = s_obj.history(period="2y")
                    
                    if not df_hist.empty:
                        # 1. Grandmaster Rule Check
                        is_minervini = check_minervini_template(df_hist)
                        if not is_minervini: continue # Wajib lolos Minervini
                        
                        # 2. 🧠 AI Engine Scoring
                        try: news_data = s_obj.news
                        except: news_data = []
                        
                        ai_score, ai_tag = deepquant_ai_score(df_hist, news_data)
                        
                        # AI Strict Mode Check
                        if ai_strict_mode and ai_score < 70: continue
                        
                        atr = calculate_atr(df_hist)
                        lp = float(row['close'])
                        sl_price = float(lp - (atr * ts_sensitivity)) 
                        sl_pct = round(((lp - sl_price) / lp) * 100, 1)
                        
                        if t_sym not in st.session_state['history_log']['Ticker'].values:
                            new_p = pd.DataFrame([[datetime.now().strftime('%H:%M'), t_sym, lp, lp, lp, sl_price, 'OPEN']], 
                                                columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
                            st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_p], ignore_index=True)
                        
                        valid_stocks += 1
                        
                        # UI Tampilan AI
                        st.markdown(f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{t_sym} <span style='color:#3fb950; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='margin:10px 0;'>
                                    <span class='badge-ai'>🧠 AI Score: {ai_score}% | {ai_tag}</span>
                                    <span class='badge-pro' style='background:#d4af37; color:black;'>🏆 Minervini Strict</span>
                                    <span class='badge-pro' style='background:#8b5cf6; color:white;'>ATR: {round(atr,1)}</span>
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("ENTRY", int(lp))
                        c2.metric("TRAILING STOP", int(sl_price), f"-{sl_pct}%")
                        
                        risk_rp = lp - sl_price
                        lot = int(((capital * (risk_pct/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                        if not ihsg_safe: lot = int(lot/2)
                        c3.metric("AI REC. LOT", lot)
                        
                        pesan_tele += f"\n💎 <b>{t_sym}</b>\n🧠 AI Score: {ai_score}% ({ai_tag})\nEntry: Rp {int(lp)}\nTrailing SL: Rp {int(sl_price)}\nLot: {lot} Lot\n"

                if valid_stocks > 0 and send_telegram:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                
                st.session_state['last_scan'] = datetime.now().strftime('%H:%M:%S')
                status.update(label=f"AI Processing Complete at {st.session_state['last_scan']}", state="complete", expanded=False)
                if valid_stocks == 0: st.warning("AI DeepQuant tidak menemukan saham dengan probabilitas kemenangan tinggi hari ini.")
            else: st.info("Market sideways.")
        except Exception as e: st.error(f"AI System Error: {e}")