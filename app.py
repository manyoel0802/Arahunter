import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings
from datetime import datetime
from tradingview_screener import Query, Column

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V43.0", layout="wide", page_icon="🏛️")

try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-inst { background: linear-gradient(135deg, #020617 0%, #3f3f46 50%, #171717 100%); border-top: 5px solid #d4d4d8; box-shadow: 0 4px 20px rgba(212, 212, 216, 0.2); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #d4d4d8; }
    .matrix-box { background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 🏛️ INSTITUTIONAL ENGINES ---
@st.cache_data(ttl=600)
def get_ihsg_data():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="1mo")
        ihsg_return = ((ihsg['Close'].iloc[-1] / ihsg['Close'].iloc[0]) - 1) * 100
        is_bullish = ihsg['Close'].iloc[-1] > ihsg['Close'].rolling(20).mean().iloc[-1]
        return is_bullish, ihsg_return
    except: return True, 0.0

ihsg_aman, ihsg_return_1mo = get_ihsg_data()

def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def detect_squeeze(df):
    try:
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
        df['Band_Width'] = (df['Upper'] - df['Lower']) / df['SMA20']
        current_bw = df['Band_Width'].iloc[-1]
        min_bw_month = df['Band_Width'].tail(20).min()
        return current_bw <= (min_bw_month * 1.1) 
    except: return False

def check_minervini_template(df):
    try:
        if len(df) < 200: return False
        c, sma50, sma150, sma200 = df['Close'].iloc[-1], df['Close'].rolling(50).mean().iloc[-1], df['Close'].rolling(150).mean().iloc[-1], df['Close'].rolling(200).mean().iloc[-1]
        return (c > sma150 and c > sma200 and sma150 > sma200 and sma50 > sma150 and c > sma50)
    except: return False

def check_smart_money(df):
    try:
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        return obv.iloc[-1] > obv.rolling(20).mean().iloc[-1]
    except: return False

def analyze_institutional_metrics(ticker, df_hist):
    try:
        # 1. Fundamental Check
        info = yf.Ticker(f"{ticker}.JK").info
        eps = info.get('trailingEps', 0) or 0
        is_profitable = eps > 0
        
        # 2. Liquidity Check (Turnover > 5 Miliar)
        avg_vol_5d = df_hist['Volume'].tail(5).mean()
        avg_price_5d = df_hist['Close'].tail(5).mean()
        turnover = avg_vol_5d * avg_price_5d
        is_liquid = turnover >= 5_000_000_000
        
        # 3. Relative Strength (Sector Rotation Proxy) - Mengalahkan IHSG 1 Bulan Terakhir
        if len(df_hist) >= 21:
            stock_return_1mo = ((df_hist['Close'].iloc[-1] / df_hist['Close'].iloc[-21]) - 1) * 100
            is_leading = stock_return_1mo > ihsg_return_1mo
        else:
            stock_return_1mo = 0
            is_leading = False
            
        return is_profitable, eps, is_liquid, turnover, is_leading, stock_return_1mo
    except: return True, 0, True, 10e9, True, 0

# --- UI HEADER ---
st.markdown(f"""
<div class='status-card bg-inst'>
    <h1 style='margin:0; color:#f4f4f5;'>🏛️ GOD MODE V43.0: THE INSTITUTIONAL ORACLE</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#a1a1aa;'>
        Relative Strength (Alpha) | Liquidity Filter > 5B | Early Warning System (Anti-Delay)
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Command Center")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    auto_pilot = st.toggle("🤖 Auto-Pilot Mode", value=False)
    
    st.divider()
    st.header("🛡️ Filter Lapis Baja")
    strict_rs = st.toggle("👑 Wajib Leading Sector", value=True, help="Hanya beli saham yang performanya mengalahkan IHSG.")
    strict_liquid = st.toggle("💧 Wajib Likuid (> Rp 5M)", value=True, help="Anti saham tidur/gaib yang tidak bisa dijual.")
    
    st.divider()
    st.header("⚙️ Capital & Risk")
    capital = st.number_input("Portfolio (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Max Loss Per Trade (%)", 0.5, 5.0, 2.0, step=0.5)
    atr_multiplier = st.slider("Batas Toleransi SL (ATR)", 1.0, 3.5, 2.0, step=0.1)

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE INSTITUTIONAL SCAN", use_container_width=True, type="primary") or auto_pilot:
    with st.status("Menganalisa Alpha, Likuiditas, dan Konfirmasi Konteks...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia')
                 .select('name','close','volume','sector')
                 .where(Column('market_cap_basic') >= 1e11))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_scan = df_raw.head(50) 
                pesan_tele = f"🏛️ <b>V43.0 INSTITUTIONAL REPORT</b>\n"
                valid_stocks = 0
                
                for idx, row in df_scan.iterrows():
                    if valid_stocks >= 3: break 
                    
                    t_sym = row['name']
                    s_obj = yf.Ticker(f"{t_sym}.JK")
                    df_hist = s_obj.history(period="1y")
                    
                    if not df_hist.empty and check_minervini_template(df_hist):
                        
                        is_profit, eps, is_liquid, turnover, is_leading, stock_ret = analyze_institutional_metrics(t_sym, df_hist)
                        
                        if strict_liquid and not is_liquid: continue
                        if strict_rs and not is_leading: continue
                        if not is_profit: continue
                        
                        if detect_squeeze(df_hist) and check_smart_money(df_hist):
                            atr = calculate_atr(df_hist)
                            lp = float(row['close'])
                            
                            sma20 = df_hist['Close'].rolling(20).mean().iloc[-1]
                            
                            # ALTERNATIF DELAY 15 MENIT: MENGHITUNG TRIGGER PRICE
                            # Robot memberi instruksi untuk pasang jebakan harga, bukan beli sekarang.
                            trigger_price = int(max(sma20, lp))
                            
                            sl_price = int(trigger_price - (atr * atr_multiplier)) 
                            target_price = int(trigger_price + (atr * 4.0)) 
                            
                            risk_rp = trigger_price - sl_price
                            rrr = round((target_price - trigger_price) / risk_rp, 1) if risk_rp > 0 else 0
                            
                            if rrr < 2.0: continue 
                            
                            sl_pct = round(((trigger_price - sl_price) / trigger_price) * 100, 1)
                            lot = int(((capital * (risk_pct/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                            if lot == 0: continue
                            
                            valid_stocks += 1
                            
                            turnover_m = turnover / 1_000_000_000
                            
                            # ---> UI One-Liner agar bebas bug kotak putih <---
                            html_card = f"<div class='stock-card'><h2 style='margin:0;'>{t_sym} <span style='color:#d4d4d8; font-size:14px; border:1px solid #d4d4d8; padding:2px 6px; border-radius:4px;'>INSTITUTIONAL SETUP</span></h2><p style='color:#a1a1aa; font-size:14px; margin:0 0 10px 0;'>Sektor: <b>{row['sector']}</b> | Turnover: <b>Rp {turnover_m:.1f} Miliar/hari</b></p><div class='matrix-box'><p style='margin:0 0 5px 0; color:#d4d4d8; font-weight:bold; font-size:12px; text-transform:uppercase;'>The Confluence Matrix:</p><ul style='margin:0; padding-left:20px; font-size:14px; color:#10b981; line-height:1.6;'><li><b>Likuiditas (> 5M):</b> Aman, uang raksasa bisa masuk/keluar tanpa <i>slippage</i> parah.</li><li><b>Relative Strength:</b> Mengalahkan IHSG ({stock_ret:.1f}% vs {ihsg_return_1mo:.1f}%). Sedang dikoleksi bandar!</li><li><b>Fundamental:</b> Perusahaan sehat (EPS Rp {eps}).</li><li><b>Momentum:</b> Volatilitas Squeeze terkonfirmasi. Siap meledak.</li></ul></div><div style='background-color:#0f172a; border-left:4px solid #3b82f6; padding:12px; margin-top:15px; border-radius:4px;'><p style='margin:0; font-size:13px; color:#93c5fd;'><b>🚨 ANTI-DELAY PROTOCOL (SOP):</b> Jangan langsung Hajar Kanan. Pasang <b>Auto-Order/Price Alert</b> di sekuritas Anda pada harga <b>Rp {trigger_price}</b>. Biarkan sistem sekuritas yang mengeksekusi secara <i>real-time</i>.</p></div></div>"
                            st.markdown(html_card, unsafe_allow_html=True)
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("🎯 TRIGGER PRICE", f"Rp {trigger_price}")
                            c2.metric("🛡️ STOP LOSS", sl_price, f"-{sl_pct}%")
                            c3.metric("📦 MAX LOT", lot)
                            
                            pesan_tele += f"\n👑 <b>{t_sym} (INSTITUTIONAL)</b>\n💧 Liquid: Rp {turnover_m:.1f} M\n💪 Alpha: {stock_ret:.1f}% (> IHSG)\n🚨 <b>PASANG AUTO-ORDER: Rp {trigger_price}</b>\n🛡️ SL: Rp {sl_price}\n📦 Lot: {lot} Lot\n"

                if valid_stocks > 0 and send_telegram:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                
                status.update(label=f"Scan Selesai!", state="complete", expanded=False)
                if valid_stocks == 0: st.warning("Sistem Institusi menolak semua saham hari ini. Tidak ada yang memenuhi syarat Kualitas, Likuiditas, dan Alpha secara bersamaan.")
            else: st.info("Gagal menarik data.")
        except Exception as e:
            st.error(f"Engine Error: {e}")