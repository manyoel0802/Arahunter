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

st.set_page_config(
    page_title="GOD MODE V13.1", 
    layout="centered", 
    page_icon="🤖"
)

# --- KREDENSIAL TERKUNCI ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
TELE_CHAT_ID = "5916986433"

# --- STYLE CSS (Tampilan Bersih & Profesional) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stock-card {
        background-color: #1c2128;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .badge {
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: bold;
        color: white;
    }
    .bg-bullish { background-color: #238636; }
    .bg-bearish { background-color: #da3633; }
    .bg-neutral { background-color: #6e7681; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE HISTORY (Session State) ---
if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Tape', 'AI'])

# --- ENGINES (Logika V13) ---
def analyze_sentiment(news_list):
    if not news_list: return "Neutral", "bg-neutral"
    pos = ['laba', 'naik', 'untung', 'kontrak', 'ekspansi', 'positif', 'rekor', 'akuisisi']
    neg = ['rugi', 'turun', 'anjlok', 'kasus', 'negatif', 'sanksi']
    score = sum(1 for n in news_list for w in pos if w in n['title'].lower()) - \
            sum(1 for n in news_list for w in neg if w in n['title'].lower())
    if score > 0: return "Bullish", "bg-bullish"
    if score < 0: return "Bearish", "bg-bearish"
    return "Neutral", "bg-neutral"

def get_tape_strength(row):
    # Mengukur efisiensi pergerakan harga vs volume
    body = abs(row['close'] - row['open'])
    range_total = abs(row['high'] - row['low']) if row['high'] != row['low'] else 0.01
    strength = (body / range_total) * row['v_ratio']
    if strength > 2.0: return "BIG FISH ENTRY", "🔥"
    if strength > 1.2: return "ACCUMULATING", "✅"
    return "NORMAL FLOW", "⚖️"

def hitung_atr(df):
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
    return tr.rolling(14).mean().iloc[-1]

def get_full_analysis(ticker, row_data):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        if df.empty or len(df) < 50: return None
        
        last_p = df['Close'].iloc[-1]
        atr = hitung_atr(df)
        
        # SMC Support
        df['Bin'] = df['Close'].round(-1)
        poc = df.groupby('Bin')['Volume'].sum().idxmax()
        
        # Trading Plan
        sl, tp = int(last_p - (1.5 * atr)), int(last_p + (3 * atr))
        sent_label, sent_class = analyze_sentiment(s.news)
        tape_label, tape_icon = get_tape_strength(row_data)
        
        # Chart
        df_p = df.tail(40)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'])])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="#58a6ff", width=2, dash="dot")))
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        
        return {"fig": fig, "sl": sl, "tp": tp, "news": s.news[:3], "sent": sent_label, "s_class": sent_class, "tape": tape_label, "t_icon": tape_icon}
    except: return None

# --- SIDEBAR (History & Settings) ---
with st.sidebar:
    st.header("📊 History Log")
    if not st.session_state['history'].empty:
        st.dataframe(st.session_state['history'].tail(10), use_container_width=True)
        if st.button("🧹 Clear History"):
            st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Harga', 'Tape', 'AI'])
            st.rerun()
    else: st.info("Belum ada riwayat.")
    st.divider()
    st.header("⚙️ Settings")
    capital = st.number_input("Modal (Rp)", value=10000000)
    risk_pct = st.slider("Risiko (%)", 1, 5, 2)
    manual_tele = st.toggle("Kirim Telegram", value=True)

# --- MAIN UI ---
st.title("🤖 GOD MODE V13.1")
st.markdown(f"**Status:** <span class='badge bg-bullish'>INTELLIGENCE READY</span> | {datetime.now().strftime('%H:%M')}", unsafe_allow_html=True)

if st.button("🚀 JALANKAN MASTER SCAN", use_container_width=True, type="primary"):
    with st.spinner("Menganalisa Sinyal & Sentimen..."):
        try:
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','SMA200','open','high','low','market_cap_basic')
                 .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
            _, df = q.get_scanner_data()
            
            if not df.empty:
                df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
                df = df[(df['market_cap_basic'] >= 5e11) & (df['v_ratio'] >= 1.5)]
                df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                pesan_tele = f"🤖 <b>AI INTELLIGENCE REPORT</b>\n"
                
                for idx, row in df.iterrows():
                    res = get_full_analysis(row['name'], row)
                    if res:
                        # Log ke Database Sidebar
                        new_log = pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(row['close']), res['tape'], res['sent']]], 
                                              columns=['Waktu', 'Ticker', 'Harga', 'Tape', 'AI'])
                        st.session_state['history'] = pd.concat([st.session_state['history'], new_log], ignore_index=True)
                        
                        # Tampilan Rapi per Saham
                        st.markdown(f"""
                        <div class='stock-card'>
                            <h3 style='margin:0;'>{row['name']} (+{round(row['change'],2)}%)</h3>
                            <span class='badge {res['s_class']}'>{res['sent']} AI</span>
                            <span style='margin-left:10px;'>{res['t_icon']} {res['tape']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        t1, t2, t3 = st.tabs(["🎯 Plan", "📉 Chart", "📰 News"])
                        with t1:
                            c1, c2, c3 = st.columns(3)
                            c1.metric("ENTRY", int(row['close']))
                            c2.metric("TARGET", res['tp'])
                            c3.metric("SL", res['sl'])
                            
                            risk_rp = capital * (risk_pct/100)
                            lot = int((risk_rp / (row['close'] - res['sl'])) / 100) if (row['close'] - res['sl']) > 0 else 0
                            st.info(f"💡 Rekomendasi: **{lot} Lot** (Risiko Rp {int(risk_rp):,})")
                        
                        with t2:
                            st.plotly_chart(res['fig'], use_container_width=True)
                        
                        with t3:
                            for n in res['news']:
                                st.write(f"• **{n['title']}** ({n['publisher']})")
                        
                        pesan_tele += f"\n🚀 <b>{row['name']}</b>\nTape: {res['t_icon']} AI: {res['sent']}\nTP: {res['tp']} | SL: {res['sl']}\n"
                
                if manual_tele:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", 
                                  data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
            else:
                st.info("Kondisi pasar sedang flat.")
        except Exception as e:
            st.error(f"Error: {e}")