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

st.set_page_config(page_title="GOD MODE V30.0", layout="wide", page_icon="🔱")

# --- SECURITY & DATABASE ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=[
        'Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'
    ])
if 'last_scan' not in st.session_state:
    st.session_state['last_scan'] = "Belum ada scan"

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-frontier { background: linear-gradient(135deg, #111827 0%, #4c1d95 50%, #f43f5e 100%); border-top: 5px solid #fbbf24; box-shadow: 0 4px 20px rgba(244, 63, 94, 0.4); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #f43f5e; }
    .badge-pro { padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .badge-alert { padding: 4px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; background: #ef4444; color: white; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 🔱 INSTITUTIONAL APEX ENGINES ---
@st.cache_data(ttl=300)
def get_macro_data():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="1mo")
        sp500 = yf.Ticker("^GSPC").history(period="1mo")
        ihsg_safe = ihsg['Close'].iloc[-1] > ihsg['Close'].rolling(20).mean().iloc[-1]
        sp500_safe = sp500['Close'].iloc[-1] > sp500['Close'].rolling(20).mean().iloc[-1]
        is_flash_crash = ((ihsg['Close'].iloc[-1] - ihsg['Close'].iloc[-2]) / ihsg['Close'].iloc[-2]) <= -0.012
        return ihsg_safe, sp500_safe, is_flash_crash, ihsg
    except: return True, True, False, pd.DataFrame()

# 1. OBV Smart Money Flow
def check_smart_money(df):
    try:
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        obv_sma20 = obv.rolling(20).mean()
        is_accumulating = obv.iloc[-1] > obv_sma20.iloc[-1]
        return is_accumulating
    except: return False

# 2. Volume Profile (Point of Control)
def calculate_poc(df, days=120):
    try:
        recent = df.tail(days).copy()
        recent['bins'] = pd.cut(recent['Close'], bins=20)
        poc_bin = recent.groupby('bins')['Volume'].sum().idxmax()
        poc_price = poc_bin.mid
        return int(poc_price), (df['Close'].iloc[-1] > poc_price)
    except: return 0, False

# 3. 5-Year Seasonality
def calculate_seasonality(ticker):
    try:
        hist = yf.Ticker(f"{ticker}.JK").history(period="5y", interval="1mo")
        if hist.empty or len(hist) < 12: return "N/A"
        
        current_month = datetime.now().month
        hist['Month'] = hist.index.month
        month_data = hist[hist['Month'] == current_month]
        if month_data.empty: return "N/A"
        
        month_data['Ret'] = (month_data['Close'] - month_data['Open']) / month_data['Open']
        win_rate = (month_data['Ret'] > 0).mean() * 100
        return f"{int(win_rate)}%"
    except: return "N/A"

def calculate_rsi(data, periods=14):
    close_delta = data['Close'].diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    ma_up = up.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    ma_down = down.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    rsi = ma_up / ma_down
    return 100 - (100/(1 + rsi))

def deepquant_ai_score(df):
    try:
        df['RSI'] = calculate_rsi(df)
        curr_rsi = df['RSI'].iloc[-1]
        rsi_score = 100 if 55 <= curr_rsi <= 75 else (curr_rsi if curr_rsi < 55 else 40)
        
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Upper_BB'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower_BB'] = df['SMA20'] - (df['STD20'] * 2)
        bb_width = (df['Upper_BB'] - df['Lower_BB']) / df['SMA20']
        
        vcp_score = 100 if bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1] else 40
        final_score = int((rsi_score * 0.5) + (vcp_score * 0.5))
        
        tag = "🌌 APEX CONVICTION" if final_score >= 85 else ("🔥 STRONG" if final_score >= 70 else "⚖️ NEUTRAL")
        return final_score, tag
    except: return 50, "⚖️ NEUTRAL"

def check_minervini_template(df):
    try:
        if len(df) < 200: return False
        c, sma50, sma150, sma200 = df['Close'].iloc[-1], df['Close'].rolling(50).mean().iloc[-1], df['Close'].rolling(150).mean().iloc[-1], df['Close'].rolling(200).mean().iloc[-1]
        low_52, high_52 = df['Low'].rolling(252).min().iloc[-1], df['High'].rolling(252).max().iloc[-1]
        return (c > sma150 and c > sma200 and sma150 > sma200 and sma50 > sma150 and c > sma50 and c >= (low_52 * 1.30) and c >= (high_52 * 0.75))
    except: return False

def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def update_trailing_stops(base_atr_mult, is_flash_crash, send_tele_active):
    if st.session_state['history_log'].empty: return
    active_atr_mult = 1.5 if is_flash_crash else base_atr_mult
    
    for index, row in st.session_state['history_log'].iterrows():
        if row['Status'] == 'OPEN':
            try:
                t = yf.Ticker(f"{row['Ticker']}.JK")
                hist = t.history(period="1mo")
                if hist.empty: continue
                
                cp, atr = float(hist['Close'].iloc[-1]), calculate_atr(hist)
                old_hwm, old_sl, entry_price = float(row['High_Water_Mark']), float(row['Trailing_SL']), float(row['Entry'])
                
                current_hwm = max(old_hwm, cp)
                st.session_state['history_log'].at[index, 'Current_Price'] = cp
                st.session_state['history_log'].at[index, 'High_Water_Mark'] = current_hwm
                
                new_trailing_sl = current_hwm - (atr * active_atr_mult)
                final_sl = max(old_sl, new_trailing_sl)
                st.session_state['history_log'].at[index, 'Trailing_SL'] = final_sl
                
                if cp <= final_sl:
                    profit_pct = ((cp - entry_price) / entry_price) * 100
                    icon = "🟢" if profit_pct > 0 else "🔴"
                    msg = f"🛡️ <b>TRAILING STOP HIT!</b>\nStock: <b>{row['Ticker']}</b>\nExit Price: {int(cp)}\nResult: {icon} <b>{round(profit_pct, 2)}%</b>\n{('⚠️ AUTO-TIGHTEN AKTIF' if is_flash_crash else '')}"
                    if send_tele_active: requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": msg, "parse_mode": "HTML"})
                    st.session_state['history_log'].at[index, 'Status'] = 'CLOSED'
            except: continue

# --- UI HEADER ---
ihsg_safe, sp500_safe, is_flash_crash, ihsg_df = get_macro_data()
flash_msg = "<br><span class='badge-alert'>⚠️ FLASH CRASH DETECTED: Trailing Stop Diperketat!</span>" if is_flash_crash else ""

st.markdown(f"""
    <div class='status-card bg-frontier'>
        <h1 style='margin:0; color:#fbbf24;'>🔱 GOD MODE V30.0: THE FINAL FRONTIER</h1>
        <p style='margin:5px 0 0 0; opacity:0.9; color:#e2e8f0;'>🇮🇩 IHSG: <b>{'BULLISH' if ihsg_safe else 'BEARISH'}</b> | 🇺🇸 S&P 500: <b>{'BULLISH' if sp500_safe else 'BEARISH'}</b>{flash_msg}</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Apex Control")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    auto_pilot = st.toggle("🤖 Auto-Pilot Mode", value=False)
    refresh_rate = st.slider("Interval (Menit)", 1, 15, 5, disabled=not auto_pilot)
    
    st.divider()
    st.header("⚙️ Capital & Risk")
    capital = st.number_input("Portfolio Size (Rp)", value=10000000, step=1000000)
    base_risk = st.slider("Base Risk Per Trade (%)", 1.0, 5.0, 2.0, step=0.5)
    ts_sensitivity = st.select_slider("Default Trailing (ATR):", options=[1.5, 2.0, 2.5, 3.0], value=2.5)
    
    st.divider()
    st.write("**📡 Quantum Tracker:**")
    active_portfolio = st.session_state['history_log'][st.session_state['history_log']['Status'] == 'OPEN']
    
    if not active_portfolio.empty:
        display_df = active_portfolio[['Ticker', 'Current_Price', 'Trailing_SL']].copy()
        display_df['Current_Price'] = pd.to_numeric(display_df['Current_Price'], errors='coerce')
        display_df['Trailing_SL'] = pd.to_numeric(display_df['Trailing_SL'], errors='coerce')
        display_df['Jarak SL'] = ((display_df['Current_Price'] - display_df['Trailing_SL']) / display_df['Current_Price'] * 100).round(1).astype(str) + '%'
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else: st.info("Tidak ada posisi terbuka.")
        
    if st.button("🧹 Clear Tracker"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
        st.rerun()

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE FRONTIER SCAN", use_container_width=True, type="primary") or auto_pilot:
    with st.status("Initializing Institutional Quant Algorithms (Please wait...)", expanded=True) as status:
        try:
            update_trailing_stops(ts_sensitivity, is_flash_crash, send_telegram)
            
            if not ihsg_safe and not sp500_safe:
                st.error("🚨 GLOBAL MARKET CRASH: Trading dilarang oleh sistem untuk melindungi kas.")
                status.update(label="Scan Dibatalkan.", state="complete")
            else:
                q = (Query().set_markets('indonesia').select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','open','high','low')
                     .where(Column('change') >= 1.5, Column('close') > Column('SMA50')))
                _, df_raw = q.get_scanner_data()
                
                if not df_raw.empty:
                    df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                    df_scan = df_raw[(df_raw['market_cap_basic'] >= 1e11) & (df_raw['v_ratio'] >= 1.5)]
                    df_scan = df_scan.sort_values('change', ascending=False).head(15).reset_index(drop=True) # Perbesar jaring awal
                    
                    pesan_tele = f"🔱 <b>V30.0 FINAL FRONTIER REPORT</b>\n"
                    valid_stocks = 0
                    current_month_name = datetime.now().strftime("%B")
                    
                    for idx, row in df_scan.iterrows():
                        if valid_stocks >= 3: break 
                        
                        t_sym = row['name']
                        s_obj = yf.Ticker(f"{t_sym}.JK")
                        df_hist = s_obj.history(period="2y")
                        
                        if not df_hist.empty and check_minervini_template(df_hist):
                            ai_score, ai_tag = deepquant_ai_score(df_hist)
                            if ai_score < 70: continue
                            
                            # 🔱 FINAL FRONTIER CHECKS
                            is_smart_money_in = check_smart_money(df_hist)
                            poc_price, above_poc = calculate_poc(df_hist)
                            seasonality_win_rate = calculate_seasonality(t_sym)
                            
                            atr = calculate_atr(df_hist)
                            lp = float(row['close'])
                            sl_price = float(lp - (atr * ts_sensitivity)) 
                            sl_pct = round(((lp - sl_price) / lp) * 100, 1)
                            
                            adjusted_risk = base_risk
                            if ai_score >= 85 and is_smart_money_in and above_poc: adjusted_risk = base_risk * 1.5 
                            elif ai_score < 75: adjusted_risk = base_risk * 0.5 
                            
                            risk_rp = lp - sl_price
                            lot = int(((capital * (adjusted_risk/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                            
                            if t_sym not in st.session_state['history_log']['Ticker'].values:
                                new_p = pd.DataFrame([[datetime.now().strftime('%H:%M'), t_sym, lp, lp, lp, sl_price, 'OPEN']], 
                                                    columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
                                st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_p], ignore_index=True)
                            
                            valid_stocks += 1
                            
                            st.markdown(f"""
                                <div class='stock-card'>
                                    <h2 style='margin:0;'>{t_sym} <span style='color:#f43f5e; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                    <p style='margin:10px 0 5px 0;'>
                                        <span style='background:#f43f5e; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;'>🧠 AI: {ai_score}%</span>
                                        <span style='background:#d4af37; color:black; padding:3px 8px; border-radius:4px; font-weight:bold;'>🏆 Minervini</span>
                                        <span style='background:{"#22c55e" if is_smart_money_in else "#64748b"}; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;'>🐋 OBV Akumulasi</span>
                                    </p>
                                    <p style='margin:0; font-size:13px; color:#94a3b8;'>
                                        🎯 <b>Volume POC (6Bln):</b> Rp {poc_price} ({'Aman, Harga di atas POC' if above_poc else 'Warning: Di bawah POC'})<br>
                                        📅 <b>Histori {current_month_name} (5 Thn):</b> Win-Rate {seasonality_win_rate}
                                    </p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("ENTRY", int(lp))
                            c2.metric("TRAILING STOP", int(sl_price), f"-{sl_pct}%")
                            c3.metric("REC. LOT", lot)
                            
                            pesan_tele += f"\n💎 <b>{t_sym}</b>\n🧠 Score: {ai_score}%\n🐋 OBV: {'Akumulasi' if is_smart_money_in else 'Distribusi'}\n📅 Win-Rate {current_month_name}: {seasonality_win_rate}\nEntry: Rp {int(lp)}\nLot: {lot} Lot\n"

                    if valid_stocks > 0 and send_telegram:
                        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                    
                    st.session_state['last_scan'] = datetime.now().strftime('%H:%M:%S')
                    status.update(label=f"Frontier Scan Complete at {st.session_state['last_scan']}", state="complete", expanded=False)
                    if valid_stocks == 0: st.warning("Mesin kuantitatif tidak menemukan saham dewa hari ini.")
        except Exception as e: st.error(f"Engine Error: {e}")

if auto_pilot:
    st.sidebar.success(f"🤖 Auto-Pilot Aktif. Memantau setiap {refresh_rate} menit...")
    time.sleep(refresh_rate * 60)
    st.rerun()