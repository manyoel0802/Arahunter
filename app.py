import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
import requests
import warnings
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI SISTEM & TEMA ---
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(
    page_title="GOD MODE V14.1", 
    layout="centered", 
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# --- KREDENSIAL TERKUNCI ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
TELE_CHAT_ID = "5916986433"

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background: #0e1117; }
    .stock-card {
        background-color: #1c2128;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .badge-bullish { background-color: #238636; color: white; }
    .badge-bearish { background-color: #da3633; color: white; }
    .badge-neutral { background-color: #6e7681; color: white; }
    </style>
    """, unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Status', 'Sentiment'])

# --- ENGINES ---
def analyze_sentiment(news_list):
    if not news_list: return "Neutral", "badge-neutral"
    pos = ['laba', 'naik', 'untung', 'kontrak', 'ekspansi', 'dividen', 'akuisisi', 'positif']
    neg = ['rugi', 'turun', 'anjlok', 'kasus', 'negatif', 'sanksi']
    score = sum(1 for n in news_list for w in pos if w in n['title'].lower()) - \
            sum(1 for n in news_list for w in neg if w in n['title'].lower())
    if score > 0: return "Bullish", "badge-bullish"
    if score < 0: return "Bearish", "badge-bearish"
    return "Neutral", "badge-neutral"

def get_tape_strength(row):
    efficiency = abs(row['close'] - row['open']) / (abs(row['high'] - row['low']) if row['high'] != row['low'] else 0.01)
    strength = efficiency * row['v_ratio']
    if strength > 2.5: return "VERY STRONG BUY", "🔥"
    if strength > 1.5: return "ACCUMULATION", "✅"
    return "NORMAL", "⚖️"

def hitung_atr(df, period=14):
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def get_analysis(ticker, row_data):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        if df.empty or len(df) < 50: return None
        last_p, atr = df['Close'].iloc[-1], hitung_atr(df)
        df['Bin'] = df['Close'].round(-1)
        poc = df.groupby('Bin')['Volume'].sum().idxmax()
        sl, tp = int(last_p - (1.5 * atr)), int(last_p + (3 * atr))
        sent_label, sent_class = analyze_sentiment(s.news)
        tape_label, tape_icon = get_tape_strength(row_data)
        
        df_p = df.tail(45)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price")])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="#58a6ff", width=2, dash="dot"), name="POC"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        return {"fig": fig, "poc": poc, "sl": sl, "tp": tp, "news": s.news[:3], "sent": sent_label, "s_class": sent_class, "tape": tape_label, "t_icon": tape_icon}
    except: return None

# --- UI HEADER ---
st.title("⚡ GOD MODE HUNTER V14.1")
st.markdown(f"**Status:** <span class='badge badge-bullish'>SYSTEM READY</span> | {datetime.now().strftime('%H:%M')}", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Settings")
    total_modal = st.number_input("Capital (Rp)", value=10000000)
    risk_level = st.slider("Risk (%)", 1, 5, 2)
    manual_send = st.toggle("📤 Sync Telegram", value=True)
    if st.button("🧹 Clear Log"):
        st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Status', 'Sentiment'])
        st.rerun()
    st.dataframe(st.session_state['history'].tail(5), use_container_width=True)

btn_scan = st.button("🚀 START SCAN SEQUENCE", use_container_width=True, type="primary")

if btn_scan:
    try:
        q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','SMA200','market_cap_basic','open','high','low')
             .where(Column('change') >= 2.0, Column('close') > Column('SMA50'), Column('close') > Column('SMA200')))
        _, df = q.get_scanner_data()
        
        if not df.empty:
            # PERBAIKAN BARIS 142
            df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
            df = df[(df['market_cap_basic'] >= 5e11) & (df['v_ratio'] >= 1.5)]
            df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
            
            pesan_tele = f"⚡ <b>GOD MODE RADAR</b>\n"
            
            for idx, row in df.iterrows():
                res = get_analysis(row['name'], row)
                if res:
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(row['close']), res['tape'], res['sent']]], columns=['Waktu', 'Ticker', 'Harga', 'Status', 'Sentiment'])])
                    
                    st.markdown(f"<div class='stock-card'><h3>{idx+1}. {row['name']} (+{round(row['change'],2)}%)</h3><span class='badge {res['s_class']}'>{res['sent']}</span> <span style='margin-left:10px;'>{res['t_icon']} {res['tape']}</span></div>", unsafe_allow_html=True)
                    
                    t1, t2, t3 = st.tabs(["🎯 Setup", "📈 Chart", "📰 News"])
                    with t1:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("ENTRY", int(row['close']))
                        c2.metric("TARGET", res['tp'])
                        c3.metric("SL", res['sl'])
                        
                        risk_rp = total_modal * (risk_level/100)
                        lot = int((risk_rp / (row['close'] - res['sl'])) / 100) if (row['close'] - res['sl']) > 0 else 0
                        st.info(f"💡 Saran: **{lot} Lot**")
                    with t2: st.plotly_chart(res['fig'], use_container_width=True)
                    with t3:
                        for n in res['news']: st.write(f"• **{n['title']}**")
                    
                    pesan_tele += f"\n💎 <b>{row['name']}</b> (+{round(row['change'],2)}%)\nEntry: {int(row['close'])}\nTP: {res['tp']} | SL: {res['sl']}\n"
            
            if manual_send:
                requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
        else:
            st.warning("No data found.")
    except Exception as e:
        st.error(f"Error: {e}")