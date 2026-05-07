import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings
from tradingview_screener import Query, Column

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V44.0", layout="wide", page_icon="🌍")

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
    .bg-sector { background: linear-gradient(135deg, #2e1065 0%, #4c1d95 50%, #3b0764 100%); border-top: 5px solid #8b5cf6; box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #8b5cf6; }
    .sector-badge { background-color: #8b5cf6; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 🌍 SECTOR ROTATION ENGINES ---
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
        return df['Band_Width'].iloc[-1] <= (df['Band_Width'].tail(20).min() * 1.1) 
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

def check_fundamentals_and_liquidity(ticker, df_hist):
    try:
        eps = yf.Ticker(f"{ticker}.JK").info.get('trailingEps', 0) or 0
        turnover = df_hist['Volume'].tail(5).mean() * df_hist['Close'].tail(5).mean()
        return eps > 0, eps, turnover >= 5_000_000_000, turnover
    except: return True, 0, True, 10e9

# --- UI HEADER ---
st.markdown("""
<div class='status-card bg-sector'>
    <h1 style='margin:0; color:#ddd6fe;'>🌍 GOD MODE V44.0: APEX SECTOR</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#a78bfa;'>
        Dynamic Sector Rotation | Top 3 Leading Sectors Only | Institutional Grade
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Command Center")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    
    st.divider()
    st.header("🛡️ Top-Down Filter")
    strict_sector = st.toggle("👑 Wajib Top 3 Sektor", value=True, help="Hanya memindai saham yang berada di 3 sektor terkuat di IHSG saat ini.")
    strict_liquid = st.toggle("💧 Wajib Likuid (> Rp 5M)", value=True)
    
    st.divider()
    st.header("⚙️ Capital & Risk")
    capital = st.number_input("Portfolio (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Max Loss Per Trade (%)", 0.5, 5.0, 2.0, step=0.5)

# --- EXECUTION ENGINE ---
if st.button("🚀 SCAN TOP 3 SECTORS", use_container_width=True, type="primary"):
    with st.status("Membaca Aliran Uang Antar Sektor...", expanded=True) as status:
        try:
            # TAHAP 1: MENGHITUNG KEKUATAN SEKTOR (SECTOR ROTATION)
            q = (Query().set_markets('indonesia')
                 .select('name','close','volume','sector','Perf.1M','market_cap_basic')
                 .where(Column('market_cap_basic') >= 1e11))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                # Membersihkan data sektor yang kosong
                df_raw = df_raw.dropna(subset=['sector', 'Perf.1M'])
                
                # Menghitung rata-rata performa 1 bulan tiap sektor
                sector_perf = df_raw.groupby('sector')['Perf.1M'].mean().sort_values(ascending=False)
                top_3_sectors = sector_perf.head(3).index.tolist()
                
                st.write("### 🏆 Top 3 Sektor Pembawa Uang (Bulan Ini):")
                for i, sec in enumerate(top_3_sectors):
                    st.success(f"{i+1}. **{sec}** (Performa: +{sector_perf[sec]:.2f}%)")
                
                # TAHAP 2: MEMFILTER SAHAM HANYA DI TOP 3 SEKTOR
                if strict_sector:
                    df_scan = df_raw[df_raw['sector'].isin(top_3_sectors)].head(50)
                else:
                    df_scan = df_raw.head(50)
                
                st.write(f"Mencari Setup Sempurna di {len(df_scan)} saham pilihan...")
                
                # TAHAP 3: ANALISA TEKNIKAL & FUNDAMENTAL
                pesan_tele = f"🌍 <b>V44.0 APEX SECTOR REPORT</b>\n"
                valid_stocks = 0
                
                for idx, row in df_scan.iterrows():
                    if valid_stocks >= 3: break 
                    
                    t_sym = row['name']
                    df_hist = yf.Ticker(f"{t_sym}.JK").history(period="1y")
                    
                    if not df_hist.empty and check_minervini_template(df_hist):
                        is_profit, eps, is_liquid, turnover = check_fundamentals_and_liquidity(t_sym, df_hist)
                        
                        if strict_liquid and not is_liquid: continue
                        if not is_profit: continue
                        
                        if detect_squeeze(df_hist) and check_smart_money(df_hist):
                            atr = calculate_atr(df_hist)
                            lp = float(row['close'])
                            sma20 = df_hist['Close'].rolling(20).mean().iloc[-1]
                            
                            trigger_price = int(max(sma20, lp))
                            sl_price = int(trigger_price - (atr * 2.0)) 
                            target_price = int(trigger_price + (atr * 4.0)) 
                            
                            risk_rp = trigger_price - sl_price
                            rrr = round((target_price - trigger_price) / risk_rp, 1) if risk_rp > 0 else 0
                            
                            if rrr < 2.0: continue 
                            
                            sl_pct = round(((trigger_price - sl_price) / trigger_price) * 100, 1)
                            lot = int(((capital * (risk_pct/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                            if lot == 0: continue
                            
                            valid_stocks += 1
                            turnover_m = turnover / 1_000_000_000
                            rank_sektor = top_3_sectors.index(row['sector']) + 1 if row['sector'] in top_3_sectors else "Lainnya"
                            
                            html_card = f"<div class='stock-card'><h2 style='margin:0;'>{t_sym} <span class='sector-badge'>SEKTOR RANK #{rank_sektor}</span></h2><p style='color:#a1a1aa; font-size:14px; margin:0 0 10px 0;'>Sektor: <b>{row['sector']}</b> | Turnover: Rp {turnover_m:.1f} Miliar/hari</p><div style='background-color:#0d1117; padding:15px; border-radius:8px; border:1px solid #30363d; margin-top:10px;'><p style='margin:0 0 5px 0; color:#d4d4d8; font-weight:bold; font-size:12px; text-transform:uppercase;'>The Top-Down Matrix:</p><ul style='margin:0; padding-left:20px; font-size:14px; color:#10b981; line-height:1.6;'><li><b>Macro Context:</b> Berada di dalam sektor yang paling banyak dibeli institusi bulan ini.</li><li><b>Fundamental:</b> Terbukti mencetak Laba (EPS Rp {eps}).</li><li><b>Teknikal:</b> Uptrend, Squeeze terkonfirmasi, dan akumulasi OBV valid.</li></ul></div><div style='background-color:#1e1b4b; border-left:4px solid #8b5cf6; padding:12px; margin-top:15px; border-radius:4px;'><p style='margin:0; font-size:13px; color:#c4b5fd;'><b>🚨 ANTI-DELAY SOP:</b> Pasang <b>Auto-Order</b> di harga <b>Rp {trigger_price}</b>. Target Profit di Rp {target_price} (RRR {rrr}x).</p></div></div>"
                            st.markdown(html_card, unsafe_allow_html=True)
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("🎯 TRIGGER PRICE", f"Rp {trigger_price}")
                            c2.metric("🛡️ STOP LOSS", sl_price, f"-{sl_pct}%")
                            c3.metric("📦 MAX LOT", lot)
                            
                            pesan_tele += f"\n🌍 <b>{t_sym} (TOP SECTOR #{rank_sektor})</b>\nSektor: {row['sector']}\n🚨 <b>AUTO-ORDER: Rp {trigger_price}</b>\n🛡️ SL: Rp {sl_price}\n📦 Lot: {lot} Lot\n"

                if valid_stocks > 0 and send_telegram:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                
                status.update(label=f"Scan Top-Down Selesai!", state="complete", expanded=False)
                if valid_stocks == 0: st.warning("Mesin tidak menemukan saham dengan setup sempurna di dalam 3 Sektor Teratas. Cash is King untuk hari ini.")
            else: st.error("Gagal menarik data sektor dari pasar.")
        except Exception as e:
            st.error(f"Engine Error: {e}")