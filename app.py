import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import time
import warnings
from tradingview_screener import Query, Column

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

# --- 🚀 KONFIGURASI SISTEM ---
st.set_page_config(page_title="V44.1 APEX SECTOR", layout="wide", page_icon="🌍")

# Pengaturan Kredensial Telegram
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    # Ganti dengan Token & Chat ID Anda jika tidak menggunakan Streamlit Secrets
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-sector { background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #064e3b 100%); border-top: 5px solid #10b981; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #10b981; }
    .sector-badge { background-color: #10b981; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 🧠 QUANTITATIVE ENGINES ---
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
        df['BW'] = (df['Upper'] - df['Lower']) / df['SMA20']
        return df['BW'].iloc[-1] <= (df['BW'].tail(20).min() * 1.1) 
    except: return False

def check_minervini_template(df):
    try:
        if len(df) < 200: return False
        c = df['Close'].iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        sma150 = df['Close'].rolling(150).mean().iloc[-1]
        sma200 = df['Close'].rolling(200).mean().iloc[-1]
        l_52 = df['Low'].rolling(252).min().iloc[-1]
        h_52 = df['High'].rolling(252).max().iloc[-1]
        return (c > sma150 and c > sma200 and sma150 > sma200 and sma50 > sma150 and c > sma50 and c >= l_52*1.3 and c >= h_52*0.75)
    except: return False

def check_smart_money(df):
    try:
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        return obv.iloc[-1] > obv.rolling(20).mean().iloc[-1]
    except: return False

# --- UI HEADER ---
st.markdown("""
<div class='status-card bg-sector'>
    <h1 style='margin:0; color:#ecfdf5;'>🦅 V44.1 APEX SECTOR: HIBRIDA</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#a7f3d0;'>
        Rotasi Sektor + SOP Scaling Out | Sinyal Otomatis ke Telegram
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Command Center")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    
    st.divider()
    st.header("⚙️ Capital & Risk")
    capital = st.number_input("Portfolio (Rp)", value=50000000, step=1000000)
    risk_pct = st.slider("Max Loss Per Trade (%)", 0.5, 3.0, 2.0, step=0.5)

# --- EXECUTION ENGINE ---
if st.button("🚀 SCAN TOP 3 SECTORS", use_container_width=True, type="primary"):
    with st.status("Menganalisa Aliran Dana Sektoral...", expanded=True) as status:
        try:
            # TAHAP 1: SECTOR ROTATION
            q = (Query().set_markets('indonesia')
                 .select('name','close','volume','sector','Perf.1M','market_cap_basic')
                 .where(Column('market_cap_basic') >= 1e11))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw = df_raw.dropna(subset=['sector', 'Perf.1M'])
                sector_perf = df_raw.groupby('sector')['Perf.1M'].mean().sort_values(ascending=False)
                top_3_sectors = sector_perf.head(3).index.tolist()
                
                st.write("### 🏆 Sektor Pemimpin Saat Ini:")
                for i, sec in enumerate(top_3_sectors):
                    st.success(f"{i+1}. **{sec}** (+{sector_perf[sec]:.2f}%)")
                
                df_scan = df_raw[df_raw['sector'].isin(top_3_sectors)].head(50)
                
                pesan_tele = f"🦅 <b>LAPORAN V44.1 APEX HIBRIDA</b>\n"
                valid_stocks = 0
                
                for idx, row in df_scan.iterrows():
                    t_sym = row['name']
                    time.sleep(1.2) # Anti-Rate Limit
                    df_hist = yf.Ticker(f"{t_sym}.JK").history(period="2y")
                    
                    if not df_hist.empty and check_minervini_template(df_hist):
                        if detect_squeeze(df_hist) and check_smart_money(df_hist):
                            atr = calculate_atr(df_hist)
                            lp = float(row['close'])
                            sma20 = df_hist['Close'].rolling(20).mean().iloc[-1]
                            
                            trigger_price = int(max(sma20, lp))
                            sl_price = int(trigger_price - (atr * 2.0)) 
                            target_price = int(trigger_price + (atr * 4.0)) 
                            
                            # LOGIKA HIBRIDA: Trailing Stop untuk sisa 50% pasukan
                            ts_dist = atr * 2.5
                            ts_pct = round((ts_dist / trigger_price) * 100, 1)
                            
                            risk_rp = trigger_price - sl_price
                            if risk_rp > 0:
                                lot = int(((capital * (risk_pct/100)) / risk_rp) / 100)
                                if lot == 0: continue
                                
                                valid_stocks += 1
                                rank_sektor = top_3_sectors.index(row['sector']) + 1
                                
                                # Tampilan Card
                                html_card = f"""
                                <div class='stock-card'>
                                    <h2 style='margin:0;'>{t_sym} <span class='sector-badge'>TOP SEKTOR #{rank_sektor}</span></h2>
                                    <div style='background-color:#111827; padding:15px; border-radius:8px; border:1px solid #30363d; margin-top:10px;'>
                                        <p style='margin:0; color:#10b981; font-weight:bold;'>SOP HIBRIDA AKTIF:</p>
                                        <ul style='font-size:14px; color:#d1d5db; line-height:1.6;'>
                                            <li>Beli <b>{lot} Lot</b> di Harga <b>Rp {trigger_price}</b></li>
                                            <li>Jual <b>50% ({lot//2} Lot)</b> di Target <b>Rp {target_price}</b></li>
                                            <li>Sisa 50% dikawal <b>Trailing Stop {ts_pct}%</b> dari harga pucuk.</li>
                                        </ul>
                                    </div>
                                </div>
                                """
                                st.markdown(html_card, unsafe_allow_html=True)
                                
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("🎯 ENTRY", f"Rp {trigger_price}")
                                c2.metric("🛡️ SL AWAL", f"Rp {sl_price}")
                                c3.metric("💰 TP (50%)", f"Rp {target_price}")
                                c4.metric("📈 TS (50%)", f"{ts_pct}%")
                                
                                pesan_tele += f"\n🎯 <b>{t_sym}</b> (Sektor: {row['sector']})\n"
                                pesan_tele += f"• Beli: {lot} Lot @ Rp {trigger_price}\n"
                                pesan_tele += f"• TP (50%): Rp {target_price}\n"
                                pesan_tele += f"• TS (50%): <b>{ts_pct}%</b>\n"

                if valid_stocks > 0 and send_telegram:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                
                status.update(label=f"Scan Selesai! {valid_stocks} Sinyal Ditemukan.", state="complete", expanded=False)
            else: st.error("Gagal menarik data sektor.")
        except Exception as e:
            st.error(f"Engine Error: {e}")