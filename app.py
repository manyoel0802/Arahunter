import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import requests
import warnings
import time
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI SISTEM ---
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V32.0", layout="wide", page_icon="🌪️")

# --- SECURITY & DATABASE ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=[
        'Waktu', 'Ticker', 'Sector', 'Entry', 'Current_Price', 'Trailing_SL', 'Status'
    ])
if 'last_scan' not in st.session_state:
    st.session_state['last_scan'] = "Belum ada scan"

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-nexus { background: linear-gradient(135deg, #020617 0%, #064e3b 50%, #0ea5e9 100%); border-top: 5px solid #10b981; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #10b981; }
    .badge-pro { padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 🌪️ SECTOR ROTATION ENGINE ---
def analyze_sector_flow(df_raw):
    try:
        # Hitung lonjakan volume per saham
        df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0, 1)
        
        # Kelompokkan berdasarkan Sektor
        sector_group = df_raw.groupby('sector').agg(
            avg_change=('change', 'mean'),
            avg_v_ratio=('v_ratio', 'mean'),
            stock_count=('name', 'count')
        ).reset_index()
        
        # Filter sektor yang isinya minimal 5 saham agar datanya valid
        sector_group = sector_group[sector_group['stock_count'] >= 5]
        
        # Hitung Momentum Score = (Kenaikan Harga x 0.6) + (Lonjakan Volume x 0.4)
        sector_group['momentum_score'] = (sector_group['avg_change'] * 0.6) + (sector_group['avg_v_ratio'] * 0.4)
        sector_group = sector_group.sort_values('momentum_score', ascending=False)
        
        # Ambil 2 Sektor Terbaik
        top_sectors = sector_group.head(2)['sector'].tolist()
        return top_sectors, sector_group
    except Exception as e:
        return [], pd.DataFrame()

# --- INSTITUTIONAL ENGINES (Dari V30) ---
@st.cache_data(ttl=300)
def get_macro_data():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="1mo")
        sp500 = yf.Ticker("^GSPC").history(period="1mo")
        ihsg_safe = ihsg['Close'].iloc[-1] > ihsg['Close'].rolling(20).mean().iloc[-1]
        sp500_safe = sp500['Close'].iloc[-1] > sp500['Close'].rolling(20).mean().iloc[-1]
        is_flash_crash = ((ihsg['Close'].iloc[-1] - ihsg['Close'].iloc[-2]) / ihsg['Close'].iloc[-2]) <= -0.012
        return ihsg_safe, sp500_safe, is_flash_crash
    except: return True, True, False

def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def deepquant_ai_score(df):
    try:
        # RSI
        close_delta = df['Close'].diff()
        up = close_delta.clip(lower=0).ewm(com=13, adjust=True, min_periods=14).mean()
        down = (-1 * close_delta.clip(upper=0)).ewm(com=13, adjust=True, min_periods=14).mean()
        rsi = 100 - (100/(1 + (up/down)))
        curr_rsi = rsi.iloc[-1]
        rsi_score = 100 if 55 <= curr_rsi <= 75 else (curr_rsi if curr_rsi < 55 else 40)
        
        # VCP
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        bb_width = ((df['SMA20'] + (df['STD20'] * 2)) - (df['SMA20'] - (df['STD20'] * 2))) / df['SMA20']
        vcp_score = 100 if bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1] else 40
        
        final_score = int((rsi_score * 0.5) + (vcp_score * 0.5))
        return final_score
    except: return 50

def check_smart_money(df):
    try:
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        return obv.iloc[-1] > obv.rolling(20).mean().iloc[-1]
    except: return False

def check_minervini_template(df):
    try:
        if len(df) < 200: return False
        c, sma50, sma150, sma200 = df['Close'].iloc[-1], df['Close'].rolling(50).mean().iloc[-1], df['Close'].rolling(150).mean().iloc[-1], df['Close'].rolling(200).mean().iloc[-1]
        low_52, high_52 = df['Low'].rolling(252).min().iloc[-1], df['High'].rolling(252).max().iloc[-1]
        return (c > sma150 and c > sma200 and sma150 > sma200 and sma50 > sma150 and c > sma50 and c >= (low_52 * 1.30) and c >= (high_52 * 0.75))
    except: return False

# --- UI HEADER ---
ihsg_safe, sp500_safe, is_flash_crash = get_macro_data()
flash_msg = "<br><span style='background:#ef4444; color:white; padding:2px 8px; border-radius:4px;'>⚠️ FLASH CRASH DETECTED</span>" if is_flash_crash else ""

st.markdown(f"""
<div class='status-card bg-nexus'>
    <h1 style='margin:0; color:#10b981;'>🌪️ GOD MODE V32.0: SECTOR NEXUS</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#e2e8f0;'>Top-Down Approach | Institutional Sector Flow | AI DeepQuant{flash_msg}</p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Flow Control")
    strict_sector = st.toggle("🌪️ Strict Sector Mode", value=True, help="Hanya beli saham yang berada di Top 2 Sektor paling panas hari ini.")
    capital = st.number_input("Portfolio (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1.0, 5.0, 2.0, step=0.5)
    
    if st.button("🧹 Clear Tracker"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Sector', 'Entry', 'Current_Price', 'Trailing_SL', 'Status'])
        st.rerun()

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE TOP-DOWN SCAN", use_container_width=True, type="primary"):
    with st.status("Helicopter View: Mapping Global & Sector Flow...", expanded=True) as status:
        try:
            # 1. Tarik Data Seluruh Pasar
            q = (Query().set_markets('indonesia')
                 .select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','sector')
                 .where(Column('market_cap_basic') >= 1e11))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                # 2. SECTOR ROTATION ANALYZER
                top_sectors, sector_df = analyze_sector_flow(df_raw)
                
                st.write("📊 **Sector Heatmap Hari Ini:**")
                st.dataframe(sector_df[['sector', 'avg_change', 'avg_v_ratio', 'momentum_score']].head(5).style.background_gradient(cmap='Greens', subset=['momentum_score']))
                
                if top_sectors:
                    st.success(f"🔥 Uang raksasa sedang mengalir deras ke Sektor: **{top_sectors[0]}** dan **{top_sectors[1]}**")
                
                # 3. Filter Saham Berdasarkan Sektor & Volume Surge
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                
                # Terapkan Strict Sector Mode jika menyala
                if strict_sector and top_sectors:
                    df_scan = df_raw[(df_raw['sector'].isin(top_sectors)) & (df_raw['change'] >= 1.5) & (df_raw['v_ratio'] >= 1.5)]
                else:
                    df_scan = df_raw[(df_raw['change'] >= 1.5) & (df_raw['v_ratio'] >= 1.5)]
                
                df_scan = df_scan.sort_values('change', ascending=False).head(15).reset_index(drop=True)
                
                pesan_tele = f"🌪️ <b>V32.0 SECTOR NEXUS REPORT</b>\n🔥 Hot Sectors: {', '.join(top_sectors[:2])}\n"
                valid_stocks = 0
                
                for idx, row in df_scan.iterrows():
                    if valid_stocks >= 3: break 
                    
                    t_sym = row['name']
                    t_sector = row['sector']
                    
                    s_obj = yf.Ticker(f"{t_sym}.JK")
                    df_hist = s_obj.history(period="2y")
                    
                    if not df_hist.empty and check_minervini_template(df_hist):
                        ai_score = deepquant_ai_score(df_hist)
                        if ai_score < 70: continue
                        
                        is_smart_money = check_smart_money(df_hist)
                        atr = calculate_atr(df_hist)
                        lp = float(row['close'])
                        sl_price = float(lp - (atr * 2.5)) 
                        sl_pct = round(((lp - sl_price) / lp) * 100, 1)
                        
                        # Dynamic Risk berdasarkan Sector dan AI
                        adjusted_risk = risk_pct
                        if strict_sector and t_sector in top_sectors and is_smart_money:
                            adjusted_risk = risk_pct * 1.5 # Bet besar karena sektor mendukung!
                            
                        risk_rp = lp - sl_price
                        lot = int(((capital * (adjusted_risk/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                        
                        valid_stocks += 1
                        
                        st.markdown(f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{t_sym} <span style='color:#10b981; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='color:#94a3b8; font-size:14px; margin:0 0 10px 0;'>🏭 Sector: <b>{t_sector}</b></p>
                                <p style='margin:0 0 5px 0;'>
                                    <span style='background:#10b981; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;'>🧠 AI: {ai_score}%</span>
                                    <span style='background:#d4af37; color:black; padding:3px 8px; border-radius:4px; font-weight:bold;'>🏆 Minervini</span>
                                    <span style='background:{"#0ea5e9" if is_smart_money else "#64748b"}; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;'>🐋 OBV</span>
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("ENTRY", int(lp))
                        c2.metric("TRAILING STOP", int(sl_price), f"-{sl_pct}%")
                        c3.metric("REC. LOT", lot)
                        
                        pesan_tele += f"\n💎 <b>{t_sym}</b> ({t_sector})\n🧠 AI: {ai_score}% | 🐋 OBV: {'Akumulasi'}\nEntry: Rp {int(lp)}\nLot: {lot} Lot\n"

                if valid_stocks > 0 and send_telegram:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                
                status.update(label=f"Top-Down Analysis Complete!", state="complete", expanded=False)
                if valid_stocks == 0: st.warning("Meskipun ada sektor yang panas, tidak ada saham yang lolos filter AI dan Minervini di sektor tersebut hari ini.")
            else: st.info("Gagal menarik data pasar.")
        except Exception as e: st.error(f"Engine Error: {e}")