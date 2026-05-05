import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
import requests
import warnings
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI SISTEM ---
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V13.0", layout="centered", page_icon="🤖")

# --- KREDENSIAL TERKUNCI ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
TELE_CHAT_ID = "5916986433"

# --- POINT 3: DATABASE INITIALIZATION (Session State) ---
if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Status', 'Sentiment'])

# --- POINT 4: NLP SENTIMENT ENGINE ---
def analyze_sentiment(news_list):
    if not news_list: return "Neutral", "⚪"
    
    pos_words = ['laba', 'naik', 'untung', 'kontrak', 'ekspansi', 'dividen', 'akuisisi', 'tumbuh', 'rekor', 'positif', 'buy', 'bullish']
    neg_words = ['rugi', 'turun', 'anjlok', 'pailit', 'pkpu', 'gugatan', 'kasus', 'negatif', 'sell', 'bearish', 'sanksi', 'suspensi']
    
    score = 0
    for n in news_list:
        text = n['title'].lower()
        for pw in pos_words:
            if pw in text: score += 1
        for nw in neg_words:
            if nw in text: score -= 1
            
    if score > 0: return "Bullish", "🟢"
    elif score < 0: return "Bearish", "🔴"
    return "Neutral", "⚪"

# --- POINT 2: SMART TAPE MONITOR (Tape Reading Proxy) ---
def get_tape_strength(row):
    # Logika: Mengukur seberapa efisien kenaikan harga dibandingkan volumenya
    # Formula: (Body Candle / Range) * Volume Ratio
    body = abs(row['close'] - row['open'])
    range_total = abs(row['high'] - row['low']) if row['high'] != row['low'] else 0.01
    efficiency = body / range_total
    strength = efficiency * row['v_ratio']
    
    if strength > 2.5: return "VERY STRONG BUY (Big Fish)", "🔥"
    elif strength > 1.5: return "Accumulation (Smart Money)", "✅"
    return "Normal Flow", "⚖️"

# --- FUNGSI ANALISA UTAMA ---
def hitung_atr(df, period=14):
    tr = pd.concat([df['High'] - df['Low'], 
                    abs(df['High'] - df['Close'].shift()), 
                    abs(df['Low'] - df['Close'].shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def get_detailed_analysis(ticker, row_data):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        if df.empty or len(df) < 50: return None
        
        last_p = df['Close'].iloc[-1]
        atr = hitung_atr(df)
        
        # SMC Support
        df['Bin'] = df['Close'].round(-1)
        poc = df.groupby('Bin')['Volume'].sum().idxmax()
        
        # Risk Mgmt
        sl = int(last_p - (1.5 * atr))
        tp = int(last_p + (3 * atr))
        
        # Sentiment & Tape
        sent_label, sent_emoji = analyze_sentiment(s.news)
        tape_label, tape_emoji = get_tape_strength(row_data)
        
        # Chart
        df_p = df.tail(45)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price")])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="cyan", width=2, dash="dot"), name="POC"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        
        return {
            "fig": fig, "poc": poc, "sl": sl, "tp": tp, "news": s.news[:3], 
            "sentiment": sent_label, "sent_emoji": sent_emoji,
            "tape": tape_label, "tape_emoji": tape_emoji
        }
    except: return None

# --- UI APP ---
st.title("🤖 GOD MODE ARA Hunter (V13.0)")
st.caption("AI Sentiment Engine | Tape Reading Proxy | Scan History Database")

with st.sidebar:
    st.header("📊 Database History")
    if not st.session_state['history'].empty:
        st.dataframe(st.session_state['history'].tail(10))
        if st.button("Clear History"):
            st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Status', 'Sentiment'])
            st.rerun()
    else:
        st.write("Belum ada riwayat scan.")
    st.divider()
    manual_send = st.toggle("📤 Auto-Send Telegram", value=True)

# --- EXECUTE SCAN ---
btn_scan = st.button("🚀 EXECUTE MASTER SCAN", use_container_width=True, type="primary")

if btn_scan:
    try:
        q = (Query().set_markets('indonesia')
             .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'SMA50', 'SMA200', 'market_cap_basic', 'open', 'high', 'low')
             .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
        
        _, df = q.get_scanner_data()
        
        if not df.empty:
            df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
            df = df[(df['market_cap_basic'] >= 5e11) & (df['v_ratio'] >= 1.5)]
            df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
            
            pesan_tele = f"🤖 <b>AI INTELLIGENCE REPORT</b>\n\n"
            
            for idx, row in df.iterrows():
                res = get_detailed_analysis(row['name'], row)
                if res:
                    # Update Database History
                    new_entry = pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(row['close']), res['tape'], res['sentiment']]], 
                                            columns=['Waktu', 'Ticker', 'Harga', 'Status', 'Sentiment'])
                    st.session_state['history'] = pd.concat([st.session_state['history'], new_entry], ignore_index=True)
                    
                    with st.expander(f"⭐ {row['name']} | Tape: {res['tape_emoji']} | AI: {res['sent_emoji']}", expanded=True):
                        t1, t2, t3 = st.tabs(["📊 Tape & Analytics", "📉 Price Action", "📰 AI News Sentiment"])
                        
                        with t1:
                            c1, c2 = st.columns(2)
                            c1.metric("Tape Reading Status", res['tape'])
                            c2.metric("AI Sentiment Score", res['sentiment'])
                            st.write(f"**Trading Plan:** Entry @{int(row['close'])} | TP @{res['tp']} | SL @{res['sl']}")
                        
                        with t2:
                            st.plotly_chart(res['fig'], use_container_width=True)
                        
                        with t3:
                            for n in res['news']:
                                st.write(f"• **{n['title']}** ({n['publisher']})")
                    
                    pesan_tele += f"🚀 <b>{row['name']}</b>\nTape: {res['tape_emoji']} {res['tape']}\nAI: {res['sent_emoji']} {res['sentiment']}\nTP: {res['tp']} | SL: {res['sl']}\n\n"
            
            if manual_send:
                requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", 
                              data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                st.toast("Report sent to AI Bot")
        else:
            st.info("No high-probability stocks detected.")
    except Exception as e:
        st.error(f"System Error: {e}")