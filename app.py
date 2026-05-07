import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings
import time
from datetime import datetime
from tradingview_screener import Query, Column

# --- OPTIMASI SISTEM ---
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V35.0", layout="wide", page_icon="👁️")

# --- SECURITY & DATABASE ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=[
        'Waktu', 'Ticker', 'Sector', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'
    ])
if 'last_scan' not in st.session_state:
    st.session_state['last_scan'] = "Belum ada scan"

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-omni { background: linear-gradient(135deg, #09090b 0%, #3b0764 50%, #9333ea 100%); border-top: 5px solid #d8b4fe; box-shadow: 0 4px 20px rgba(147, 51, 234, 0.4); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #d8b4fe; }
    </style>
    """, unsafe_allow_html=True)

# --- 👁️ ENGINES & ALGORITHMS ---
def analyze_sector_flow(df_raw):
    try:
        df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0, 1)
        sector_group = df_raw.groupby('sector').agg(avg_change=('change', 'mean'), avg_v_ratio=('v_ratio', 'mean'), stock_count=('name', 'count')).reset_index()
        sector_group = sector_group[sector_group['stock_count'] >= 5]
        sector_group['momentum_score'] = (sector_group['avg_change'] * 0.6) + (sector_group['avg_v_ratio'] * 0.4)
        sector_group = sector_group.sort_values('momentum_score', ascending=False)
        return sector_group.head(2)['sector'].tolist(), sector_group
    except Exception as e: return [], pd.DataFrame()

@st.cache_data(ttl=300)
def get_macro_data():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="1mo")
        sp500 = yf.Ticker("^GSPC").history(period="1mo")
        vix = yf.Ticker("^VIX").history(period="1mo") # Indeks Ketakutan Global
        
        ihsg_safe = ihsg['Close'].iloc[-1] > ihsg['Close'].rolling(20).mean().iloc[-1]
        sp500_safe = sp500['Close'].iloc[-1] > sp500['Close'].rolling(20).mean().iloc[-1]
        is_flash_crash = ((ihsg['Close'].iloc[-1] - ihsg['Close'].iloc[-2]) / ihsg['Close'].iloc[-2]) <= -0.012
        
        vix_level = vix['Close'].iloc[-1]
        global_fear = vix_level >= 20.0 # Angka 20 adalah batas panik Wall Street
        
        return ihsg_safe, sp500_safe, is_flash_crash, global_fear, round(vix_level, 1)
    except: return True, True, False, False, 15.0

# 📰 NLP NEWS SENTIMENT ANALYZER
def analyze_stock_news(ticker):
    try:
        news_data = yf.Ticker(f"{ticker}.JK").news
        if not news_data: return "⚪ INFO: Tidak ada berita krusial terbaru.", "NETRAL"
        
        pos_words = ['laba', 'naik', 'untung', 'akuisisi', 'ekspansi', 'kontrak', 'positif', 'tumbuh', 'rekor', 'dividen', 'melonjak']
        neg_words = ['rugi', 'turun', 'anjlok', 'kasus', 'negatif', 'sanksi', 'gagal', 'susut', 'utang', 'gugatan', 'pkpu', 'suspend', 'batal', 'selidiki']
        
        score = 0
        latest_title = news_data[0].get('title', '')
        
        for n in news_data[:3]: # Cek 3 berita terbaru
            title = n.get('title', '').lower()
            if any(w in title for w in pos_words): score += 1
            if any(w in title for w in neg_words): score -= 2 # Bobot negatif lebih besar
            
        if score > 0: return f"🟢 SENTIMEN POSITIF (Headlines: {latest_title[:40]}...)", "POSITIF"
        elif score < 0: return f"🔴 AWAS! SENTIMEN NEGATIF (Headlines: {latest_title[:40]}...)", "NEGATIF"
        else: return f"🟡 SENTIMEN NETRAL (Headlines: {latest_title[:40]}...)", "NETRAL"
    except: return "⚪ Gagal memuat berita.", "NETRAL"

def check_fundamentals(ticker):
    try:
        info = yf.Ticker(f"{ticker}.JK").info
        eps = info.get('trailingEps', 0)
        roe = info.get('returnOnEquity', 0)
        if eps is None: eps = 0
        if roe is None: roe = 0
        return eps > 0, round(eps, 1), round(roe * 100, 1)
    except: return True, 0, 0 

def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def deepquant_ai_score(df):
    try:
        close_delta = df['Close'].diff()
        up = close_delta.clip(lower=0).ewm(com=13, adjust=True, min_periods=14).mean()
        down = (-1 * close_delta.clip(upper=0)).ewm(com=13, adjust=True, min_periods=14).mean()
        curr_rsi = (100 - (100/(1 + (up/down)))).iloc[-1]
        rsi_score = 100 if 55 <= curr_rsi <= 75 else (curr_rsi if curr_rsi < 55 else 40)
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        bb_width = ((df['SMA20'] + (df['STD20'] * 2)) - (df['SMA20'] - (df['STD20'] * 2))) / df['SMA20']
        vcp_score = 100 if bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1] else 40
        return int((rsi_score * 0.5) + (vcp_score * 0.5))
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

def update_trailing_stops(is_flash_crash, send_tele_active):
    if st.session_state['history_log'].empty: return
    active_atr_mult = 1.5 if is_flash_crash else 2.5
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
ihsg_safe, sp500_safe, is_flash_crash, global_fear, vix_level = get_macro_data()
flash_msg = "<br><span style='background:#ef4444; color:white; padding:2px 8px; border-radius:4px;'>⚠️ FLASH CRASH DETECTED</span>" if is_flash_crash else ""
fear_msg = f"<br><span style='background:#f97316; color:white; padding:2px 8px; border-radius:4px;'>🌎 GLOBAL FEAR INDEX TINGGI (VIX: {vix_level}) - AWAS BERITA MAKRO BURUK!</span>" if global_fear else f"<br><span style='color:#a855f7;'>🌎 VIX Global Normal ({vix_level})</span>"

st.markdown(f"""
<div class='status-card bg-omni'>
    <h1 style='margin:0; color:#d8b4fe;'>👁️ GOD MODE V35.0: THE OMNISCIENCE</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#e2e8f0;'>
        🇮🇩 IHSG: <b>{'BULLISH' if ihsg_safe else 'BEARISH'}</b> | 🇺🇸 S&P 500: <b>{'BULLISH' if sp500_safe else 'BEARISH'}</b>
        {fear_msg} {flash_msg}
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Command Center")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    auto_pilot = st.toggle("🤖 Auto-Pilot Mode", value=False)
    refresh_rate = st.slider("Interval (Menit)", 1, 15, 5, disabled=not auto_pilot)
    
    st.divider()
    st.header("🛡️ Strategy Filters")
    strict_sector = st.toggle("🌪️ Strict Sector Mode", value=True)
    strict_fundamental = st.toggle("🏛️ Strict Fundamental", value=True)
    strict_news = st.toggle("📰 Anti-Bad News", value=True, help="Otomatis menolak saham jika terdeteksi berita negatif terbaru (Misal: Kasus hukum, laporan rugi).")
    
    st.divider()
    st.header("⚙️ Capital & Risk")
    capital = st.number_input("Portfolio (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 1.0, 5.0, 2.0, step=0.5)
    
    st.divider()
    st.write("**📡 Tracker Portfolio:**")
    active_portfolio = st.session_state['history_log'][st.session_state['history_log']['Status'] == 'OPEN']

    if not active_portfolio.empty:
        display_df = active_portfolio[['Ticker', 'Current_Price', 'Trailing_SL']].copy()
        display_df['Current_Price'] = pd.to_numeric(display_df['Current_Price'], errors='coerce')
        display_df['Trailing_SL'] = pd.to_numeric(display_df['Trailing_SL'], errors='coerce')
        display_df['Jarak SL'] = ((display_df['Current_Price'] - display_df['Trailing_SL']) / display_df['Current_Price'] * 100).round(1).astype(str) + '%'
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else: st.info("Tidak ada posisi terbuka.")
        
    if st.button("🧹 Clear Tracker"):
        st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Sector', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
        st.rerun()

# --- EXECUTION ENGINE ---
if st.button("🚀 INITIATE OMNISCIENCE SCAN", use_container_width=True, type="primary") or auto_pilot:
    with st.status("Omniscience Radar is Scanning Global & Local News...", expanded=True) as status:
        try:
            update_trailing_stops(is_flash_crash, send_telegram)
            
            q = (Query().set_markets('indonesia')
                 .select('name','close','change','volume','average_volume_10d_calc','SMA50','market_cap_basic','sector')
                 .where(Column('market_cap_basic') >= 1e11))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                top_sectors, sector_df = analyze_sector_flow(df_raw)
                
                st.write("📊 **Sector Heatmap Hari Ini:**")
                st.dataframe(sector_df[['sector', 'avg_change', 'avg_v_ratio', 'momentum_score']].head(5), use_container_width=True)
                
                if top_sectors: st.success(f"🔥 Sektor Hot Uang Raksasa: **{top_sectors[0]}** & **{top_sectors[1]}**")
                
                df_raw['v_ratio'] = df_raw['volume'] / df_raw['average_volume_10d_calc'].replace(0,1)
                
                if strict_sector and top_sectors:
                    df_scan = df_raw[(df_raw['sector'].isin(top_sectors)) & (df_raw['change'] >= 1.5) & (df_raw['v_ratio'] >= 1.5)]
                else:
                    df_scan = df_raw[(df_raw['change'] >= 1.5) & (df_raw['v_ratio'] >= 1.5)]
                
                df_scan = df_scan.sort_values('change', ascending=False).head(15).reset_index(drop=True)
                
                pesan_tele = f"👁️ <b>V35.0 OMNISCIENCE REPORT</b>\n"
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
                        
                        is_profitable, eps, roe = check_fundamentals(t_sym)
                        if strict_fundamental and not is_profitable: continue 
                        
                        # 📰 CEK BERITA (NEWS SENTIMENT)
                        news_msg, sentiment_status = analyze_stock_news(t_sym)
                        if strict_news and sentiment_status == "NEGATIF": continue # Buang saham jika ada bad news!
                        
                        is_smart_money = check_smart_money(df_hist)
                        atr = calculate_atr(df_hist)
                        lp = float(row['close'])
                        
                        sma20 = df_hist['Close'].rolling(20).mean().iloc[-1]
                        best_entry = int(max(sma20, lp - (atr * 0.5)))
                        
                        distance_to_ma = ((lp - sma20) / sma20) * 100
                        if distance_to_ma > 6.0:
                            timing_status = "⏳ TUNGGU (Harga Terlalu Tinggi, Antre Bawah)"
                            timing_bg = "#f59e0b" 
                        else:
                            timing_status = "🚀 BELI HARI INI (Area Ideal)"
                            timing_bg = "#10b981"
                        
                        sl_price = float(lp - (atr * 2.5)) 
                        sl_pct = round(((lp - sl_price) / lp) * 100, 1)
                        
                        adjusted_risk = risk_pct
                        if strict_sector and t_sector in top_sectors and is_smart_money: adjusted_risk = risk_pct * 1.5 
                        if global_fear: adjusted_risk = risk_pct * 0.5 # Kurangi risiko 50% jika dunia sedang panik
                            
                        risk_rp = lp - sl_price
                        lot = int(((capital * (adjusted_risk/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                        
                        if t_sym not in st.session_state['history_log']['Ticker'].values:
                            new_p = pd.DataFrame([[datetime.now().strftime('%H:%M'), t_sym, t_sector, lp, lp, lp, sl_price, 'OPEN']], 
                                                columns=['Waktu', 'Ticker', 'Sector', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])
                            st.session_state['history_log'] = pd.concat([st.session_state['history_log'], new_p], ignore_index=True)
                        
                        valid_stocks += 1
                        
                        st.markdown(f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{t_sym} <span style='color:#d8b4fe; font-size:18px;'>+{round(row['change'],2)}%</span></h2>
                                <p style='color:#94a3b8; font-size:14px; margin:0 0 5px 0;'>🏭 Sector: <b>{t_sector}</b> | 🏛️ EPS: <b>Rp {eps}</b></p>
                                <p style='margin:0 0 10px 0;'>
                                    <span style='background:#10b981; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;'>🧠 AI: {ai_score}%</span>
                                    <span style='background:#d4af37; color:black; padding:3px 8px; border-radius:4px; font-weight:bold;'>🏆 Minervini</span>
                                    <span style='background:{"#0ea5e9" if is_smart_money else "#64748b"}; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;'>🐋 OBV</span>
                                </p>
                                <p style='margin:0 0 10px 0; font-size:14px; color:#cbd5e1;'>📰 <b>News Tracker:</b> {news_msg}</p>
                                <div style='background-color:{timing_bg}; color:white; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px; text-align:center; margin-bottom:15px;'>
                                    {timing_status}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("🎯 ZONA BELI TERBAIK", f"Rp {best_entry} - {int(lp)}")
                        c2.metric("🛡️ TRAILING STOP", int(sl_price), f"-{sl_pct}%")
                        c3.metric("📦 REC. LOT", lot)
                        
                        pesan_tele += f"\n💎 <b>{t_sym}</b> ({t_sector})\n📰 News: {sentiment_status}\n⚡ {timing_status}\n🎯 Buy: Rp {best_entry} - Rp {int(lp)}\n🛡️ SL: Rp {int(sl_price)}\n📦 Lot: {lot} Lot\n"

                if valid_stocks > 0 and send_telegram:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                
                st.session_state['last_scan'] = datetime.now().strftime('%H:%M:%S')
                status.update(label=f"Omniscience Scan Complete at {st.session_state['last_scan']}!", state="complete", expanded=False)
                if valid_stocks == 0: st.warning("Semua saham yang lolos filter di-blokir oleh filter Fundamental atau Sentimen Berita Buruk hari ini.")
            else: st.info("Gagal menarik data pasar.")
        except Exception as e: st.error(f"Engine Error: {e}")

# --- AUTO-PILOT ---
if auto_pilot:
    st.sidebar.success(f"🤖 Auto-Pilot Aktif. Memantau setiap {refresh_rate} menit...")
    time.sleep(refresh_rate * 60)
    st.rerun()