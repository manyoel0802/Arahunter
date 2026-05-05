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

st.set_page_config(page_title="GOD MODE ARA Hunter", layout="centered", page_icon="🏦")

# --- KREDENSIAL TERKUNCI (HARDCODED) ---
TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
TELE_CHAT_ID = "5916986433"

st.title("🏦 GOD MODE ARA Hunter (V11.3)")
st.caption("Auto-Configured | ATR Trading Plan | News Sentiment | SMC Support")

# --- SETTING MODAL (Tampilan Utama) ---
with st.expander("💰 Pengaturan Modal & Risiko", expanded=True):
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        total_modal = st.number_input("Total Modal (Rp)", value=10000000, step=1000000)
    with col_m2:
        risk_per_trade = st.slider("Risiko Per Trade (%)", 1, 5, 2)

# --- FUNGSI KIRIM TELEGRAM ---
def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    payload = {"chat_id": TELE_CHAT_ID, "text": pesan, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=5)
    except:
        pass

# --- FUNGSI ANALISA TEKNIKAL ---
def hitung_atr(df, period=14):
    tr = pd.concat([df['High'] - df['Low'], 
                    abs(df['High'] - df['Close'].shift()), 
                    abs(df['Low'] - df['Close'].shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def get_advanced_analysis(ticker):
    try:
        s = yf.Ticker(f"{ticker}.JK")
        df = s.history(period="1y")
        if df.empty or len(df) < 50: return None
        
        atr = hitung_atr(df)
        last_p = df['Close'].iloc[-1]
        
        # SMC Support (Point of Control)
        df['Price_Bin'] = df['Close'].round(-1)
        poc = df.groupby('Price_Bin')['Volume'].sum().idxmax()
        
        # Risk Management (Analisa Trader Pro)
        sl = int(last_p - (1.5 * atr))
        tp = int(last_p + (3 * atr))
        diff = last_p - sl
        lot = int(((total_modal * (risk_per_trade/100)) / diff) / 100) if diff > 0 else 0
        
        # Chart Plotting
        df_p = df.tail(40)
        fig = go.Figure(data=[go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price")])
        fig.add_trace(go.Scatter(x=[df_p.index[0], df_p.index[-1]], y=[poc, poc], line=dict(color="cyan", width=2, dash="dot"), name="SMC POC"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        
        return {"fig": fig, "poc": poc, "sl": sl, "tp": tp, "lots": lot, "news": s.news[:3]}
    except:
        return None

# --- TOMBOL KONTROL UTAMA ---
st.divider()
c_send, c_auto = st.columns([1,1])
with c_send:
    manual_send = st.toggle("📤 Aktifkan Kirim Telegram", value=False)
with c_auto:
    mode_auto = st.toggle("🔄 Auto-Scan (15 Menit)", value=False)

btn_scan = st.button("🚀 JALANKAN RADAR SEKARANG", use_container_width=True, type="primary")

# --- LOGIKA EKSEKUSI ---
if btn_scan:
    st.caption(f"Radar Engine Active: {datetime.now().strftime('%H:%M:%S')} WIB")
    try:
        q = (Query().set_markets('indonesia')
             .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'SMA50', 'SMA200', 'market_cap_basic', 'open', 'high')
             .where(Column('change') >= 2.0, Column('close') > Column('SMA50'), Column('close') > Column('SMA200')))
        
        _, df = q.get_scanner_data()
        
        if not df.empty:
            # Filter Volume & Market Cap (>500M)
            df['v_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0,1)
            df = df[(df['market_cap_basic'] >= 5e11) & (df['v_ratio'] >= 1.5)]
            df['is_trap'] = (df['high'] - df[['open', 'close']].max(axis=1)) > (2 * abs(df['close'] - df['open']).replace(0,0.01))
            
            # Ranking Top 5
            df = df.sort_values('change', ascending=False).head(5).reset_index(drop=True)
            
            if not df.empty:
                st.success(f"💎 Radar mengunci {len(df)} saham 'High Probability'.")
                pesan_tele = f"🏦 <b>GOD MODE REPORT</b>\n🕒 {datetime.now().strftime('%H:%M')}\n\n"
                
                for idx, row in df.iterrows():
                    res = get_advanced_analysis(row['name'])
                    if res:
                        with st.container():
                            medali = ["🏆", "🥈", "🥉", "📌", "📌"][idx]
                            st.subheader(f"{medali} Rank #{idx+1}: {row['name']} (+{round(row['change'],2)}%)")
                            
                            if row['is_trap']: st.error("⚠️ STATUS: TRAP/DISTRIBUSI (Hati-hati Pucuk!)")
                            else: st.success("✅ STATUS: CLEAN ACCUMULATION (Siap Gas!)")
                            
                            # Info Trading Plan
                            t1, t2, t3 = st.columns(3)
                            t1.warning(f"**Entry**\nRp {int(row['close'])}")
                            t2.success(f"**Target**\nRp {res['tp']}")
                            t3.error(f"**SL**\nRp {res['sl']}")
                            
                            st.info(f"💡 Saran Alokasi: **{res['lots']} Lot** (Berdasarkan Risiko {risk_per_trade}%)")
                            st.plotly_chart(res['fig'], use_container_width=True)
                            
                            # Info News
                            if res['news']:
                                with st.expander("📰 Berita & Sentimen Terbaru"):
                                    for n in res['news']:
                                        st.write(f"**{n['title']}**")
                                        st.caption(f"Source: {n['publisher']} | [Baca Berita]({n['link']})")
                            
                            # Gabungkan Pesan Telegram (Hanya yg bukan Trap)
                            if not row['is_trap']:
                                pesan_tele += (f"{medali} <b>{row['name']}</b> (+{round(row['change'],2)}%)\n"
                                              f"Entry: {int(row['close'])}\nTarget: {res['tp']}\nSL: {res['sl']}\n"
                                              f"Size: {res['lots']} Lot\n\n")
                            st.divider()
                
                if manual_send:
                    kirim_telegram(pesan_tele)
                    st.toast("✅ Terkirim ke Telegram 5916986433")
            else:
                st.info("Tidak ada saham yang lolos filter ketat saat ini.")
        else:
            st.info("Pasar sedang tenang, tidak ada ledakan volume.")
    except Exception as e:
        st.error(f"Engine Error: {e}")

# --- LOGIKA AUTO SCAN ---
if mode_auto:
    t_minus = st.empty()
    for s in range(900, 0, -1):
        m, sec = divmod(s, 60)
        t_minus.markdown(f"### ⏳ Scan Berikutnya: {m:02d}:{sec:02d}")
        time.sleep(1)
    st.rerun()