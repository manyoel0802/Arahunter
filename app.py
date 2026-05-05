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

st.set_page_config(page_title="GOD MODE V24.0", layout="wide", page_icon="🎯")

# --- SECURITY ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- DATABASE ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=[
        'Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'
    ])

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-precision { background: linear-gradient(135deg, #0f172a 0%, #020617 100%); border-top: 5px solid #06b6d4; }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; }
    .badge-pro { padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINES ---

@st.cache_data(ttl=300)
def get_ihsg_data():
    try: return yf.Ticker("^JKSE").history(period="3mo")
    except: return pd.DataFrame()

def calculate_relative_strength(stock_df, ihsg_df):
    try:
        stock_ret = (stock_df['Close'].iloc[-1] - stock_df['Close'].iloc[-20]) / stock_df['Close'].iloc[-20]
        ihsg_ret = (ihsg_df['Close'].iloc[-1] - ihsg_df['Close'].iloc[-20]) / ihsg_df['Close'].iloc[-20]
        return round((stock_ret - ihsg_ret) * 100, 2)
    except: return 0

def check_mtfa_weekly(ticker):
    try:
        w_df = yf.Ticker(f"{ticker}.JK").history(period="1y", interval="1wk")
        sma20_w = w_df['Close'].rolling(20).mean().iloc[-1]
        return w_df['Close'].iloc[-1] > sma20_w
    except: return False

def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), 
             np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

# --- LIVE TRAILING STOP TRACKER ---
def update_trailing_stops(atr_mult):
    if st.session_state['history_log'].empty: return
    
    for index, row in st.session_state['history_log'].iterrows():
        if row['Status'] == 'OPEN':
            try:
                t = yf.Ticker(f"{row['Ticker']}.JK")
                hist = t.history(period="1mo")
                if hist.empty: continue
                
                cp = float(hist['Close'].iloc[-1])
                atr = calculate_atr(hist)
                
                # 1. Update Harga Terkini & High Water Mark
                current_hwm = max(row['High_Water_Mark'], cp)
                st.session_state['history_log'].at[index, 'Current_Price'] = cp
                st.session_state['history_log'].at[index, 'High_Water_Mark'] = current_hwm
                
                # 2. Kalkulasi Trailing Stop Dinamis
                new_trailing_sl = current_hwm - (atr * atr_mult)
                # Pastikan SL tidak pernah turun (hanya bisa naik atau diam)
                final_sl = max(row['Trailing_SL'], new_trailing_sl)
                st.session_state['history_log'].at[index, 'Trailing_SL'] = int(final_sl)
                
                # 3. Eksekusi jika harga menyentuh/melewati Trailing Stop ke bawah
                if cp <= final_sl:
                    profit_pct = ((cp - row['Entry']) / row['Entry']) * 100
                    icon = "🟢" if profit_pct > 0 else "🔴"
                    msg = f"🛡️ <b>TRAILING STOP HIT!</b>\n\nStock: <b>{row['Ticker']}</b>\nEntry: {row['Entry']}\nExit Price: {int(cp)}\nResult: {icon} <b>{round(profit_pct, 2)}%</b>\n\n<i>Silakan jual saham ini sekarang untuk mengamankan modal/profit.</i>"
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": msg, "parse_mode": "HTML"})
                    st.session_state['history_log'].at[index, 'Status'] = 'CLOSED'
            except: continue

# --- UI HEADER ---
ihsg_df = get_ihsg_data()
ihsg_safe = ihsg_df['Close'].iloc[-1] > ihsg_df['Close'].rolling(20).mean().iloc[-1] if not ihsg_df.empty else True

st.markdown(f"""
    <div class='status-card bg-precision'>
        <h1 style='margin:0; color:#22d3ee;'>🎯 GOD MODE V24.0: PRECISION SENTINEL</h1>
        <p style='margin:0; opacity:0.8; color:#e2e8f0;'>Live Trailing Stop Tracker | Adjustable ATR Accuracy</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Trailing Stop Config")
    # Fitur Baru: Pengaturan Akurasi Trailing Stop
    ts_sensitivity = st.select_slider(
        "Sensitivitas Trailing Stop (ATR Multiplier):",
        options=[1.5, 2.0, 2.5, 3.0],
        value=2.5,
        help="1.5 = Sangat Ketat (Cepat Jual), 2.5 = Normal (Pro), 3.0 = Longgar (Swing Panjang)"
    )
    
    st.divider()
    capital = st.number_input("Portfolio Size (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1.0, 3.0, 2.0, step=0.5)
    
    st.divider()
    st.write("**📡 Live Trailing Tracker:**")
    
    # Menampilkan Tracker yang Rapi
    active_portfolio = st.session_state['history_log'][st.session_state['history_log']['Status'] == 'OPEN']
    if not active_portfolio.empty:
        display_df = active_portfolio[['Ticker', 'Entry', 'Current_Price', 'Trailing_SL']].copy()
        # Hitung jarak dari harga sekarang ke Trailing SL
        display_df['Jarak ke Stop'] = ((display_df['Current_Price'] - display_df['Trailing_SL']) / display_df['Current_Price'] * 100).round(1).astype(str) + '%'
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("Portofolio kosong.")
        
    if st.button("🔄 Update Live Tracker"):
        update_trailing_stops(ts_sensitivity)
        st.rerun()
        
    if st.button("🧹 Clear Portfolio"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
        st.rerun()

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE PRECISION SCAN", use_container_width=True, type="primary"):
    with st.status("Calculating Precision Entries & Stops...", expanded=True) as status:
        try:
            # Update posisi lama sebelum mencari yang baru
            update_trailing_stops(ts_sensitivity)
            
            q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                 .where(Column('change') >= 1.5, Column('close') > Column('SMA50')))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                df_scan = df_raw[(df_raw['market_cap_basic'] >= 1e11) & (df_raw['v_ratio'] >= 1.5)]
                df_scan = df_scan.sort_values('change', ascending=False).head(8).reset_index(drop=True)
                
                valid_stocks = 0
                for idx, row in df_scan.iterrows():
                    if valid_stocks >= 3: break 
                    
                    t_sym = row['name']
                    is_weekly_bull = check_mtfa_weekly(t_sym)
                    if not is_weekly_bull: continue # Paksa tren mingguan harus naik
                    
                    s_obj = yf.Ticker(f"{t_sym}.JK")
                    df_hist = s_obj.history(period="1y")
                    
                    if not df_hist.empty:
                        rs_score = calculate_relative_strength(df_hist, ihsg_df)
                        atr = calculate_atr(df_hist)
                        
                        lp = float(row['close'])
                        # Trailing SL dihitung berdasarkan sensitivitas yang dipilih user
                        sl_price = int(lp - (atr * ts_sensitivity)) 
                        sl_pct = round(((lp - sl_price) / lp) * 100, 1)
                        
                        if t_sym not in st.session_state['history_log']['Ticker'].values:
                            new_p = pd.DataFrame([[datetime.now().strftime('%H:%M'), t_sym, int(lp), int(lp), int(lp), sl_price, 'OPEN']], 
                                                columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
                            st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_p], ignore_index=True)
                        
                        valid_stocks += 1
                        
                        st.markdown(f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{t_sym} <span style='color:#3fb950; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='margin:10px 0;'>
                                    <span class='badge-pro' style='background:#1f6feb; color:white;'>RS: {rs_score}%</span>
                                    <span class='badge-pro' style='background:#8b5cf6; color:white;'>ATR: {round(atr,1)}</span>
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("ENTRY", int(lp))
                        c2.metric("TRAILING STOP", sl_price, f"-{sl_pct}%")
                        
                        risk_rp = lp - sl_price
                        lot = int(((capital * (risk_pct/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                        if not ihsg_safe: lot = int(lot/2)
                        
                        c3.metric("REC. LOT", lot)
                        st.info(f"💡 **Info Trailing:** Batas Stop Loss adalah **{sl_pct}%** dari harga pucuk. Angka ini akan otomatis naik jika harga saham terus melambung.")

                status.update(label="Precision Scan Complete!", state="complete", expanded=False)
                if valid_stocks == 0: st.warning("Tidak ada sinyal sempurna hari ini.")
            else: st.info("Market sideways.")
        except Exception as e: st.error(f"System Error: {e}")