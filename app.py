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
    page_title="GOD MODE V15.2", 
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

# --- ENGINE ANALYTICS (Direct Fetch - No Cache to avoid Error) ---
def calculate_bandar_confidence(df, v_ratio):
    try:
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        close, low, high = df['Close'].iloc[-1], df['Low'].iloc[-1], df['High'].iloc[-1]
        ad_strength = ((close - low) - (high - close)) / (high - low) if (high - low) != 0 else 0
        score = 50 + (ad_strength * 20) + (v_ratio * 5)
        
        if score > 90: return min(score, 100), "ULTRA ACCUMULATION", "bg-accum"
        if score > 65: return score, "BIG MONEY ENTRY", "bg-inst"
        return score, "NORMAL FLOW", "bg-neu"
    except:
        return 50, "ANALYSIS N/A", "bg-neu"

def analyze_sentiment_pro(ticker_obj):
    try:
        news = ticker_obj.news
        if not news: return "NEUTRAL", 50
        pos = ['laba', 'naik', 'positif', 'kontrak', 'ekspansi', 'dividen', 'akuisisi']
        neg = ['rugi', 'turun', 'negatif', 'kasus', 'sanksi']
        score = 50
        for n in news:
            text = n['title'].lower()
            score += sum(5 for w in pos if w in text)
            score -= sum(7 for w in neg if w in text)
        return ("BULLISH" if score > 55 else "BEARISH" if score < 45 else "NEUTRAL"), score
    except:
        return "NEUTRAL", 50

# --- UI APP ---
if 'history' not in st.session_state: st.session_state['history'] = []

st.title("🦅 GOD MODE V15.2")
st.caption("Safe Mode | No-Cache Engine | Institutional Flow Analysis")

with st.sidebar:
    st.header("📊 Terminal Control")
    capital = st.number_input("Capital (Rp)", value=10000000, step=1000000)
    risk_val = st.slider("Risk Per Trade (%)", 1, 5, 2)
    st.divider()
    if st.button("🗑️ Clear Log"):
        st.session_state['history'] = []
        st.rerun()

# --- MASTER SCAN ---
if st.button("🚀 INITIATE INSTITUTIONAL RADAR", use_container_width=True, type="primary"):
    with st.status("Accessing BEI Liquidity Hub...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 5e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                if not df_scan.empty:
                    pesan_tele = f"🦅 <b>V15.2 SAFE REPORT</b>\n"
                    
                    for idx, row in df_scan.iterrows():
                        # Direct Fetch (Tanpa st.cache agar tidak error)
                        s_obj = yf.Ticker(f"{row['name']}.JK")
                        df_hist = s_obj.history(period="1y")
                        
                        if not df_hist.empty:
                            b_score, b_label, b_class = calculate_bandar_confidence(df_hist, row['v_ratio'])
                            s_label, s_score = analyze_sentiment_pro(s_obj)
                            
                            last_p = row['close']
                            sl = int(last_p * 0.96)
                            tp = int(last_p * 1.12)
                            
                            st.markdown(f"""
                                <div class='report-card'>
                                    <h2>{row['name']} (+{round(row['change'],2)}%)</h2>
                                    <span class='badge-pro {b_class}'>{b_label}</span> 
                                    <span class='badge-pro bg-inst' style='margin-left:5px;'>AI: {s_label}</span>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            t1, t2 = st.tabs(["📝 Plan", "📈 Flow Analysis"])
                            with t1:
                                c1, c2, c3 = st.columns(3)
                                c1.metric("ENTRY", int(last_p))
                                c2.metric("TARGET", tp)
                                c3.metric("STOP LOSS", sl)
                                risk_rp = capital * (risk_val/100)
                                lot = int((risk_rp / (last_p - sl)) / 100) if (last_p - sl) > 0 else 0
                                st.info(f"💼 **Execution:** Buy **{lot} Lots**")
                                
                            with t2:
                                fig = go.Figure(go.Indicator(mode="gauge+number", value=b_score, title={'text': "Bandar Confidence"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#58a6ff"}}))
                                fig.update_layout(height=200, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor='rgba(0,0,0,0)')
                                st.plotly_chart(fig, use_container_width=True)
                            
                            pesan_tele += f"\n🔥 <b>{row['name']}</b>\nConfidence: {int(b_score)}%\nTP: {tp} | SL: {sl}\n"
                    
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                    status.update(label="Scan Complete!", state="complete", expanded=False)
                else:
                    st.warning("Tidak ada saham dengan kriteria institutional flow saat ini.")
            else:
                st.info("Kondisi pasar sedang flat.")
        except Exception as e:
            st.error(f"Engine Error: {e}")