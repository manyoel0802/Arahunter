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

st.set_page_config(page_title="GOD MODE Hunter", layout="centered", page_icon="🏦")

# --- KREDENSIAL TERKUNCI ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
TELE_CHAT_ID = "5916986433"

# --- STYLE CSS AGAR RAPI ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏦 GOD MODE ARA Hunter (V12.0)")
st.caption("Ultimate Edition | Institutional Risk Manager | News & SMC Analytics")

# --- PENGATURAN MODAL ---
with st.container():
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        total_modal = st.number_input("💰 Total Modal (Rp)", value=10000000, step=1000000)
    with col_m2:
        risk_per_trade = st.slider("⚖️ Risiko Per Trade (%)", 1, 5, 2)
    st.divider()

# --- FUNGSI TOOLS ---
def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    payload = {"chat_id": TELE_CHAT_ID, "text": pesan, "parse_mode": "HTML"}
    try: requests.post(url, data=payload, timeout=5)
    except: pass

def hitung_atr(df, period=14):
    tr = pd.concat([df['High'] - df['Low'], 
                    abs(df['High'] - df['Close'].shift()), 
                    abs(df['Low'] - df['Close'].shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def get_analysis(ticker):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        if df.empty or len(df) < 50: return None
        
        last_p = df['Close'].iloc[-1]
        atr = hitung_atr(df)
        
        # SMC POC
        df['Bin'] = df['Close'].round(-1)
        poc = df.groupby('Bin')['Volume'].sum().idxmax()
        
        # Math Strategy
        sl = int(last_p - (1.5 * atr))
        tp = int(last_p + (3 * atr))
        rr_ratio = round((tp - last_p) / (last_p - sl), 2) if (last_p - sl) > 0 else 0
        
        # Position Sizing Formula: 
        # $$Lot = \frac{Modal \times \%Risk}{Harga - SL} \div 100$$
        risk_rp = total_modal * (risk_per_trade / 100)
        lot = int((risk_rp / (last_p - sl)) / 100) if (last_p - sl) > 0 else 0
        
        # Chart
        df_p = df.tail(45)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price")])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="cyan", width=2, dash="dot"), name="Support POC"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350, xaxis_rangeslider_visible=False, template="plotly_dark")
        
        return {"fig": fig, "poc": poc, "sl": sl, "tp": tp, "lots": lot, "news": s.news[:3], "rr": rr_ratio}
    except: return None

# --- TOMBOL KONTROL ---
c_send, c_auto = st.columns(2)
with c_send:
    manual_send = st.toggle("📤 Send to Telegram", value=True)
with c_auto:
    mode_auto = st.toggle("🔄 Auto-Scan 15m", value=False)

btn_scan = st.button("🚀 EXECUTE RADAR", use_container_width=True, type="primary")

# --- LOGIKA SCAN ---
if btn_scan:
    st.caption(f"Engine Status: Online | {datetime.now().strftime('%H:%M:%S')}")
    try:
        q = (Query().set_markets('indonesia')
             .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'SMA50', 'SMA200', 'market_cap_basic', 'open', 'high')
             .where(Column('change') >= 2.0, Column('close') > Column('SMA50'), Column('close') > Column('SMA200')))
        
        _, df = q.get_scanner_data()
        
        if not df.empty:
            df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
            df = df[(df['market_cap_basic'] >= 5e11) & (df['v_ratio'] >= 1.5)]
            df['is_trap'] = (df['high'] - df[['open', 'close']].max(axis=1)) > (2 * abs(df['close'] - df['open']).replace(0,0.01))
            df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
            
            if not df.empty:
                st.success(f"Ditemukan {len(df)} Saham Sinyal Kuat")
                pesan_tele = f"🏦 <b>ULTIMATE RADAR REPORT</b>\n\n"
                
                for idx, row in df.iterrows():
                    res = get_analysis(row['name'])
                    if res:
                        with st.expander(f"RANK #{idx+1}: {row['name']} (+{round(row['change'],2)}%)", expanded=True):
                            # TABS UNTUK KERAPIAN
                            tab1, tab2, tab3 = st.tabs(["🎯 Trading Plan", "📊 Chart Analysis", "📰 News & Sentiment"])
                            
                            with tab1:
                                col_p1, col_p2, col_p3 = st.columns(3)
                                col_p1.metric("Entry Price", f"Rp {int(row['close'])}")
                                col_p2.metric("Target (3x ATR)", f"Rp {res['tp']}")
                                col_p3.metric("Stop Loss", f"Rp {res['sl']}")
                                
                                st.info(f"💡 **Rekomendasi Beli:** {res['lots']} Lot (Risk: Rp {int(total_modal * (risk_per_trade/100)):,})")
                                if res['rr'] >= 2: st.success(f"💎 Risk/Reward Ratio: {res['rr']} (Sangat Layak)")
                                else: st.warning(f"⚠️ Risk/Reward Ratio: {res['rr']} (Hati-hati)")
                            
                            with tab2:
                                st.plotly_chart(res['fig'], use_container_width=True)
                                if row['is_trap']: st.error("🚨 FAKE BREAKOUT DETECTED: Bandar sedang guyur!")
                                else: st.success("✅ REAL ACCUMULATION: Institusi sedang menjaga harga.")
                            
                            with tab3:
                                if res['news']:
                                    for n in res['news']:
                                        st.write(f"**{n['title']}**")
                                        st.caption(f"[{n['publisher']}]({n['link']})")
                                else: st.write("Tidak ada berita signifikan hari ini.")
                            
                            # Siapkan Pesan Tele
                            if not row['is_trap']:
                                pesan_tele += f"🚀 <b>{row['name']}</b>\nEntry: {int(row['close'])}\nTP: {res['tp']}\nSL: {res['sl']}\nSize: {res['lots']} Lot\n\n"
                            st.divider()
                
                if manual_send:
                    kirim_telegram(pesan_tele)
                    st.toast("Pesan dikirim ke @NemuGendul_Bot")
            else: st.info("Tidak ada saham lolos filter institusi.")
        else: st.info("Pasar sedang konsolidasi.")
    except Exception as e: st.error(f"Engine Error: {e}")

# --- AUTO SCAN ---
if mode_auto:
    t_minus = st.empty()
    for s in range(900, 0, -1):
        m, sec = divmod(s, 60)
        t_minus.markdown(f"### ⏳ Refresh in: {m:02d}:{sec:02d}")
        time.sleep(1)
    st.rerun()