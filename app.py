import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import requests
import warnings
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI SISTEM ---
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V23.0", layout="wide", page_icon="👑")

# --- SECURITY ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- DATABASE ---
if 'history_log' not in st.session_state:
    # Ditambahkan 'High_Water_Mark' untuk Trailing Stop Profesional
    st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'High_Water_Mark', 'Trailing_SL', 'Status'])

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-apex { background: linear-gradient(135deg, #0f172a 0%, #000000 100%); border-top: 5px solid #fbbf24; }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; }
    .badge-pro { padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INSTITUTIONAL ENGINES ---

# 1. Market Breadth & Global Data
@st.cache_data(ttl=300)
def get_ihsg_data():
    try: return yf.Ticker("^JKSE").history(period="3mo")
    except: return pd.DataFrame()

# 2. Relative Strength (RS) vs IHSG (Apakah saham ini Pemimpin Pasar?)
def calculate_relative_strength(stock_df, ihsg_df):
    try:
        stock_ret = (stock_df['Close'].iloc[-1] - stock_df['Close'].iloc[-20]) / stock_df['Close'].iloc[-20]
        ihsg_ret = (ihsg_df['Close'].iloc[-1] - ihsg_df['Close'].iloc[-20]) / ihsg_df['Close'].iloc[-20]
        rs_score = stock_ret - ihsg_ret # Alpha Generation
        return round(rs_score * 100, 2)
    except: return 0

# 3. Multi-Timeframe Alignment (Weekly Trend Check)
def check_mtfa_weekly(ticker):
    try:
        w_df = yf.Ticker(f"{ticker}.JK").history(period="1y", interval="1wk")
        sma20_w = w_df['Close'].rolling(20).mean().iloc[-1]
        is_uptrend = w_df['Close'].iloc[-1] > sma20_w
        return is_uptrend
    except: return False

# 4. ATR & Chandelier Exit Calculation
def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), 
             np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

# 5. Chandelier Trailing Stop Sentinel
def check_chandelier_sentinel():
    if st.session_state['history_log'].empty: return
    for index, row in st.session_state['history_log'].iterrows():
        if row['Status'] == 'OPEN':
            try:
                t = yf.Ticker(f"{row['Ticker']}.JK")
                hist = t.history(period="1mo")
                cp = hist['Close'].iloc[-1]
                atr = calculate_atr(hist)
                
                # Update High Water Mark (Harga Tertinggi sejak beli)
                current_hwm = max(row['High_Water_Mark'], cp)
                st.session_state['history_log'].at[index, 'High_Water_Mark'] = current_hwm
                
                # Kalkulasi Trailing Stop (Chandelier = Highest High - 2.5 ATR)
                new_trailing_sl = current_hwm - (atr * 2.5)
                # Pastikan SL Trailing tidak pernah turun
                final_sl = max(row['Trailing_SL'], new_trailing_sl)
                st.session_state['history_log'].at[index, 'Trailing_SL'] = final_sl
                
                # Eksekusi Exit jika harga turun melewati Trailing Stop
                if cp < final_sl:
                    profit_pct = ((cp - row['Entry']) / row['Entry']) * 100
                    msg = f"🛡️ <b>CHANDELIER EXIT TRIGGERED</b>\n\nStock: <b>{row['Ticker']}</b>\nEntry: {row['Entry']}\nExit Price: {int(cp)}\nProfit/Loss: <b>{round(profit_pct, 2)}%</b>\n\n<i>Posisi ditutup oleh sistem Trailing Stop Profesional.</i>"
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": msg, "parse_mode": "HTML"})
                    st.session_state['history_log'].at[index, 'Status'] = 'CLOSED'
            except: continue

# --- UI HEADER ---
ihsg_df = get_ihsg_data()
ihsg_safe = ihsg_df['Close'].iloc[-1] > ihsg_df['Close'].rolling(20).mean().iloc[-1] if not ihsg_df.empty else True

st.markdown(f"""
    <div class='status-card bg-apex'>
        <h1 style='margin:0; color:#fbbf24;'>👑 GOD MODE V23.0: INSTITUTIONAL APEX</h1>
        <p style='margin:0; opacity:0.8; color:#e2e8f0;'>Multi-Timeframe | Relative Strength | Chandelier Trailing Stop</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Pro Config")
    capital = st.number_input("Portfolio Size (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1.0, 3.0, 2.0, step=0.5)
    strict_mtfa = st.toggle("Strict MTFA (Wajib Weekly Uptrend)", value=True)
    
    st.divider()
    st.write("**Sentinel Portfolio (Chandelier Trailing):**")
    st.dataframe(st.session_state['history_log'][st.session_state['history_log']['Status'] == 'OPEN'], use_container_width=True)
    
    if st.button("🧹 Clear Portfolio"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'High_Water_Mark', 'Trailing_SL', 'Status'])
        st.rerun()

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE INSTITUTIONAL SCAN", use_container_width=True, type="primary"):
    with st.status("Running Institutional Algorithms...", expanded=True) as status:
        try:
            check_chandelier_sentinel() # Cek trailing stop portofolio lama
            
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 1.5, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                # Filter Market Cap (Min 100 Miliar) & Volume Meledak
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 1e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(8).reset_index(drop=True)
                
                valid_stocks = 0
                for idx, row in df_scan.iterrows():
                    if valid_stocks >= 3: break # Tampilkan max 3 saham paling sempurna
                    
                    t_sym = row['name']
                    # 1. MTFA Check
                    is_weekly_bull = check_mtfa_weekly(t_sym)
                    if strict_mtfa and not is_weekly_bull: continue
                    
                    s_obj = yf.Ticker(f"{t_sym}.JK")
                    df_hist = s_obj.history(period="1y")
                    
                    if not df_hist.empty:
                        # 2. RS & ATR Check
                        rs_score = calculate_relative_strength(df_hist, ihsg_df)
                        atr = calculate_atr(df_hist)
                        
                        lp = float(row['close'])
                        sl_price = int(lp - (atr * 2.5)) # Initial Stop Loss
                        
                        # Tambah ke Portfolio
                        if t_sym not in st.session_state['history_log']['Ticker'].values:
                            new_p = pd.DataFrame([[datetime.now().strftime('%H:%M'), t_sym, int(lp), int(lp), sl_price, 'OPEN']], 
                                                columns=['Waktu', 'Ticker', 'Entry', 'High_Water_Mark', 'Trailing_SL', 'Status'])
                            st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_p], ignore_index=True)
                        
                        # UI Tampilan Institusi
                        valid_stocks += 1
                        st.markdown(f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{t_sym} <span style='color:#3fb950; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='margin:10px 0;'>
                                    <span class='badge-pro' style='background:#1f6feb; color:white;'>RS: {rs_score}% (vs IHSG)</span>
                                    <span class='badge-pro' style='background:{"#238636" if is_weekly_bull else "#6e7681"}; color:white;'>MTFA Weekly: {"BULLISH" if is_weekly_bull else "WEAK"}</span>
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("ENTRY", int(lp))
                        c2.metric("INITIAL STOP", sl_price)
                        
                        risk_rp = lp - sl_price
                        lot = int(((capital * (risk_pct/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                        if not ihsg_safe: lot = int(lot/2)
                        
                        c3.metric("REC. LOT", lot)
                        st.info("💡 **Strategi Chandelier:** Jangan jual sampai harga turun memotong garis Trailing SL di Sidebar.")

                status.update(label="Institutional Scan Complete!", state="complete", expanded=False)
                if valid_stocks == 0: st.warning("Tidak ada saham yang lolos filter ketat Institusi (MTFA & RS). Sabar, simpan cash.")
            else: st.info("Market sedang tidak menentu.")
        except Exception as e: st.error(f"System Error: {e}")