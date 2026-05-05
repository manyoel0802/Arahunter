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
    page_title="GOD MODE V16.0", 
    layout="centered", 
    page_icon="💎",
    initial_sidebar_state="expanded"
)

# --- KREDENSIAL TERKUNCI ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
TELE_CHAT_ID = "5916986433"

# --- CUSTOM CSS: LUXURY DARK TERMINAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Global Styles */
    .main { background-color: #0d1117; color: #c9d1d9; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 12px; background-color: #161b22; }
    
    /* Stock Card Header */
    .stock-card {
        padding: 15px;
        border-radius: 12px;
        background: linear-gradient(90deg, #1f242c 0%, #161b22 100%);
        border-left: 5px solid #58a6ff;
        margin-bottom: 10px;
    }
    
    /* Metrics Styling */
    div[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #58a6ff; }
    
    /* Badge Styling */
    .status-badge {
        padding: 2px 12px;
        border-radius: 15px;
        font-size: 11px;
        font-weight: bold;
        color: white;
    }
    .bg-bull { background-color: #238636; }
    .bg-bear { background-color: #da3633; }
    .bg-neu { background-color: #6e7681; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE LOG INITIALIZATION ---
if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Price', 'Signal', 'AI'])

# --- ANALYTICS ENGINES ---
def analyze_ai_sentiment(news):
    if not news: return "NEUTRAL", "bg-neu"
    pos_keywords = ['laba', 'naik', 'positif', 'kontrak', 'ekspansi', 'dividen', 'rekor', 'akuisisi']
    score = sum(1 for n in news for k in pos_keywords if k in n['title'].lower())
    return ("BULLISH", "bg-bull") if score > 0 else ("NEUTRAL", "bg-neu")

def get_tape_status(row):
    # PVA Analysis: Price Volume Action
    range_move = abs(row['high'] - row['low']) if row['high'] != row['low'] else 0.01
    efficiency = abs(row['close'] - row['open']) / range_move
    power = efficiency * row['v_ratio']
    if power > 2.0: return "BIG FISH ENTRY", "🔥"
    if power > 1.2: return "ACCUMULATING", "✅"
    return "NORMAL FLOW", "⚖️"

def hitung_atr(df):
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
    return tr.rolling(14).mean().iloc[-1]

def get_full_analysis(ticker, row_data):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        if df.empty or len(df) < 30: return None
        
        last_p = df['Close'].iloc[-1]
        atr = hitung_atr(df)
        
        # SMC Support
        df['Price_Bin'] = df['Close'].round(-1)
        poc = df.groupby('Price_Bin')['Volume'].sum().idxmax()
        
        # Trading Plan
        sl, tp = int(last_p - (1.5 * atr)), int(last_p + (3 * atr))
        ai_label, ai_class = analyze_ai_sentiment(s.news)
        tape_label, tape_icon = get_tape_status(row_data)
        
        # Simple Chart
        df_p = df.tail(40)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'])])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="#58a6ff", width=2, dash="dot")))
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=280, xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        return {"fig": fig, "sl": sl, "tp": tp, "news": s.news[:3], "ai": ai_label, "ai_class": ai_class, "tape": tape_label, "t_icon": tape_icon}
    except: return None

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Terminal Config")
    capital = st.number_input("Trading Capital (Rp)", value=10000000, step=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1, 5, 2)
    st.divider()
    manual_tele = st.toggle("Sync to Telegram", value=True)
    if st.button("🧹 Reset History"):
        st.session_state['history'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Price', 'Signal', 'AI'])
        st.rerun()
    st.caption("Last 5 Signals")
    st.table(st.session_state['history'].tail(5))

# --- MAIN INTERFACE ---
st.title("💎 GOD MODE V16.0")
st.markdown(f"**Bursa Efek Indonesia** | Status: <span class='status-badge bg-bull'>CONNECTED</span> | {datetime.now().strftime('%H:%M:%S')}", unsafe_allow_html=True)

if st.button("🚀 INITIATE MASTER SCAN", use_container_width=True, type="primary"):
    with st.status("Engines warming up...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','SMA200','open','high','low','market_cap_basic')
                 .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
            _, df = q.get_scanner_data()
            
            if not df.empty:
                df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
                df = df[(df['market_cap_basic'] >= 5e11) & (df['v_ratio'] >= 1.5)]
                df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                if not df.empty:
                    pesan_tele = f"💎 <b>ULTIMATE TRADING REPORT</b>\n"
                    
                    for idx, row in df.iterrows():
                        res = get_full_analysis(row['name'], row)
                        if res:
                            # Log to Database
                            st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([[datetime.now().strftime('%H:%M'), row['name'], int(row['close']), res['tape'], res['ai']]], columns=['Waktu', 'Ticker', 'Price', 'Signal', 'AI'])], ignore_index=True)
                            
                            # UI Card
                            st.markdown(f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{row['name']} <span style='font-size:18px; color:#3fb950;'>+{round(row['change'],2)}%</span></h2>
                                <span class='status-badge {res['ai_class']}'>AI: {res['ai']}</span>
                                <span style='margin-left:10px; font-size:14px;'>{res['t_icon']} {res['tape']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            t1, t2, t3 = st.tabs(["🎯 Setup", "📈 Analysis", "📰 News"])
                            with t1:
                                c1, c2, c3 = st.columns(3)
                                c1.metric("ENTRY", f"Rp {int(row['close'])}")
                                c2.metric("TARGET", f"Rp {res['tp']}")
                                c3.metric("STOP LOSS", f"Rp {res['sl']}")
                                
                                risk_amt = capital * (risk_pct/100)
                                lot = int((risk_amt / (row['close'] - res['sl'])) / 100) if (row['close'] - res['sl']) > 0 else 0
                                st.info(f"💡 Recommendation: Buy **{lot} Lot** (Max Risk: Rp {int(risk_amt):,})")
                            
                            with t2:
                                st.plotly_chart(res['fig'], use_container_width=True)
                            
                            with t3:
                                for n in res['news']:
                                    st.markdown(f"• **{n['title']}** <br><small>Source: {n['publisher']} | [Read Article]({n['link']})</small>", unsafe_allow_html=True)
                            
                            pesan_tele += f"\n🚀 <b>{row['name']}</b> (+{round(row['change'],2)}%)\nAI: {res['ai']} | Tape: {res['t_icon']}\nEntry: {int(row['close'])}\nTarget: {res['tp']} | SL: {res['sl']}\n"
                    
                    if manual_tele:
                        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                    status.update(label="Scanning Complete!", state="complete", expanded=False)
                else:
                    st.warning("Radar Aktif: Tidak ada sinyal yang memenuhi kriteria volume saat ini.")
            else:
                st.info("Kondisi Pasar: Flat (Tidak ada saham naik > 2% saat ini).")
                
        except Exception as e:
            st.error(f"Error pada sistem: {e}")