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
    page_title="GOD MODE V15.0", 
    layout="centered", 
    page_icon="🦅"
)

# --- KREDENSIAL TERKUNCI ---
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
    .metric-box {
        background-color: #010409;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        border: 1px solid #21262d;
    }
    .badge-pro { padding: 3px 12px; border-radius: 12px; font-size: 11px; font-weight: bold; color: white; }
    .bg-inst { background-color: #1f6feb; } /* Blue for Institutional */
    .bg-accum { background-color: #238636; } /* Green */
    .bg-dist { background-color: #da3633; } /* Red */
    </style>
    """, unsafe_allow_html=True)

# --- POINT 5: CACHING ENGINE (Optimasi Performa) ---
@st.cache_data(ttl=900) # Cache data selama 15 menit
def fetch_stock_data(ticker):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        return s, df
    except:
        return None, None

# --- POINT 1 & 2: BANDARMOLOGY & FLOW PROXY ---
def calculate_bandar_confidence(df, row):
    # Menggunakan MFI (Money Flow Index) & VSA sebagai Proxy Bandarmologi
    # $$MFI = 100 - \frac{100}{1 + Money Flow Ratio}$$
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    
    # Menghitung Accumulation/Distribution Strength
    close = df['Close'].iloc[-1]
    low = df['Low'].iloc[-1]
    high = df['High'].iloc[-1]
    ad_strength = ((close - low) - (high - close)) / (high - low) if (high - low) != 0 else 0
    
    # Final Score 0-100
    score = 50 # Base score
    score += (ad_strength * 20)
    score += (row['v_ratio'] * 5)
    if score > 90: return min(score, 100), "ULTRA ACCUMULATION", "bg-accum"
    if score > 65: return score, "BIG MONEY ENTRY", "bg-inst"
    return score, "NORMAL FLOW", "bg-neu"

# --- POINT 4: NLP SENTIMENT V2 ---
def analyze_sentiment_pro(news):
    if not news: return "NEUTRAL", 50
    pos = ['laba', 'naik', 'positif', 'kontrak', 'ekspansi', 'dividen', 'akuisisi', 'buyback', 'tumbuh']
    neg = ['rugi', 'turun', 'negatif', 'kasus', 'sanksi', 'suspensi', 'pailit', 'pkpu']
    
    score = 50
    for n in news:
        text = n['title'].lower()
        score += sum(5 for w in pos if w in text)
        score -= sum(7 for w in neg if w in text)
    
    label = "BULLISH" if score > 55 else "BEARISH" if score < 45 else "NEUTRAL"
    return label, score

# --- RISK MANAGEMENT FORMULA ---
def get_position_size(capital, risk_pct, price, sl):
    # $$Size = \frac{Capital \times Risk\%}{Price - SL} \div 100$$
    risk_amount = capital * (risk_pct / 100)
    diff = price - sl
    if diff <= 0: return 0
    return int((risk_amount / diff) / 100)

# --- UI APP ---
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.title("🦅 GOD MODE V15.0")
st.caption("Institutional Intelligence | VSA Flow | Money Flow Index | Pro-Caching")

with st.sidebar:
    st.header("📊 Terminal Control")
    capital = st.number_input("Capital (Rp)", value=10000000, step=1000000)
    risk_val = st.slider("Risk Per Trade (%)", 1, 5, 2)
    st.divider()
    if st.button("🗑️ Clear Terminal Log"):
        st.session_state['history'] = []
        st.rerun()
    st.write("**Recent Alerts:**")
    for h in st.session_state['history'][-5:]:
        st.caption(f"[{h['time']}] {h['ticker']} - {h['signal']}")

# --- MASTER SCAN ---
if st.button("🚀 INITIATE INSTITUTIONAL RADAR", use_container_width=True, type="primary"):
    with st.status("Accessing BEI Liquidity Hub...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','SMA200','open','high','low','market_cap_basic')
                 .where(Column('change') >= 2.0, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 5e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(5).reset_index(drop=True)
                
                if not df_scan.empty:
                    pesan_tele = f"🦅 <b>V15.0 INSTITUTIONAL REPORT</b>\n"
                    
                    for idx, row in df_scan.iterrows():
                        stock_info, df_hist = fetch_stock_data(row['name'])
                        if df_hist is not None:
                            # Advanced Analytics
                            b_score, b_label, b_class = calculate_bandar_confidence(df_hist, row)
                            s_label, s_score = analyze_sentiment_pro(stock_info.news)
                            
                            # Trading Plan
                            last_p = row['close']
                            sl = int(last_p * 0.96) # Standard 4% SL
                            tp = int(last_p * 1.12) # Target 12% (RR 1:3)
                            lots = get_position_size(capital, risk_val, last_p, sl)
                            
                            # UI Component
                            with st.container():
                                st.markdown(f"""
                                <div class='report-card'>
                                    <h2 style='margin:0;'>{row['name']} <span style='font-size:16px; color:#3fb950;'>+{round(row['change'],2)}%</span></h2>
                                    <span class='badge-pro {b_class}'>{b_label}</span>
                                    <span class='badge-pro bg-inst' style='margin-left:5px;'>AI SENTIMENT: {s_label}</span>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                tab1, tab2 = st.tabs(["📝 Institutional Plan", "📈 Flow Analysis"])
                                with tab1:
                                    c1, c2, c3 = st.columns(3)
                                    with c1: st.metric("ENTRY", f"Rp {int(last_p)}")
                                    with c2: st.metric("TARGET", f"Rp {tp}")
                                    with c3: st.metric("STOP LOSS", f"Rp {sl}")
                                    st.warning(f"💼 **Execution:** Buy **{lots} Lots** | Max Risk: Rp {int(capital*(risk_val/100)):,}")
                                
                                with tab2:
                                    # Confidence Gauge (Visual Score)
                                    fig_score = go.Figure(go.Indicator(
                                        mode = "gauge+number", value = b_score,
                                        title = {'text': "Bandar Confidence Score", 'font': {'size': 14}},
                                        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#58a6ff"}}
                                    ))
                                    fig_score.update_layout(height=200, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor='rgba(0,0,0,0)')
                                    st.plotly_chart(fig_score, use_container_width=True)
                                
                                # Simpan ke History Sidebar
                                st.session_state['history'].append({'time': datetime.now().strftime('%H:%M'), 'ticker': row['name'], 'signal': b_label})
                                pesan_tele += f"\n🔥 <b>{row['name']}</b>\nConfidence: {int(b_score)}% ({b_label})\nPlan: {int(last_p)} -> TP {tp}\n"
                    
                    if requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", 
                                     data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"}):
                        st.toast("Institutional Report Synced to Telegram")
                    status.update(label="Scanning Complete!", state="complete", expanded=False)
                else: st.warning("Saringan Ketat: Tidak ada saham dengan aliran uang besar saat ini.")
            else: st.info("Pasar sedang konsolidasi (Sideways).")
        except Exception as e: st.error(f"Engine Error: {e}")