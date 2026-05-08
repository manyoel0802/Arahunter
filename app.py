import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings
import time
from tradingview_screener import Query, Column
from io import BytesIO

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V44.0", layout="wide", page_icon="🌍")

# --- KREDENSIAL TELEGRAM ---
try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

# --- TEMA VISUAL KLASIK (UNGU) ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-sector { background: linear-gradient(135deg, #2e1065 0%, #4c1d95 50%, #3b0764 100%); border-top: 5px solid #8b5cf6; box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #8b5cf6; }
    .sector-badge { background-color: #8b5cf6; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .lockdown-box { background-color: #450a0a; border: 1px solid #dc2626; padding: 15px; border-radius: 8px; color: #fca5a5; margin-bottom:20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 🌍 CORE ENGINES & NEW FEATURES ---
def get_market_health():
    try:
        ihsg = yf.Ticker("^JKSE").history(period="6mo")
        ihsg['SMA50'] = ihsg['Close'].rolling(50).mean()
        curr_close = ihsg['Close'].iloc[-1]
        sma50 = ihsg['SMA50'].iloc[-1]
        return "BULLISH" if curr_close > sma50 else "BEARISH", curr_close
    except: return "NEUTRAL", 0

def quick_backtest(df):
    try:
        # Simulasi Win Rate Squeeze dalam 1 tahun terakhir (Hold 5 hari)
        df['Squeeze_Trigger'] = (df['BW'] <= df['BW'].rolling(20).min().shift(1) * 1.1) & (df['Close'] > df['SMA50'])
        df['Future_Return'] = df['Close'].shift(-5) / df['Close'] - 1
        wins = df[(df['Squeeze_Trigger'] == True) & (df['Future_Return'] > 0)]
        total = df[df['Squeeze_Trigger'] == True]
        if len(total) == 0: return 0, 0
        win_rate = (len(wins) / len(total)) * 100
        return round(win_rate, 1), len(total)
    except: return 0.0, 0

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
        c, sma50, sma150, sma200 = df['Close'].iloc[-1], df['Close'].rolling(50).mean().iloc[-1], df['Close'].rolling(150).mean().iloc[-1], df['Close'].rolling(200).mean().iloc[-1]
        return (c > sma150 and c > sma200 and sma150 > sma200 and sma50 > sma150 and c > sma50)
    except: return False

def check_smart_money(df):
    try:
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        return obv.iloc[-1] > obv.rolling(20).mean().iloc[-1]
    except: return False

def check_fundamentals(ticker, df_hist):
    try:
        eps = yf.Ticker(f"{ticker}.JK").info.get('trailingEps', 0) or 0
        turnover = df_hist['Volume'].tail(5).mean() * df_hist['Close'].tail(5).mean()
        return eps > 0, eps, turnover >= 5_000_000_000, turnover
    except: return True, 0, True, 10e9

# --- UI HEADER ---
st.markdown("""
<div class='status-card bg-sector'>
    <h1 style='margin:0; color:#ddd6fe;'>🌍 GOD MODE V44.0: HEDGE FUND EDITION</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#a78bfa;'>
        Market Breadth Lockdown | Anti-Correlation Matrix | Win-Rate Backtester
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Command Center")
    send_telegram = st.toggle("📲 Telegram Alerts", value=True)
    
    st.divider()
    st.header("🛡️ Hedge Fund Filters")
    strict_sector = st.toggle("👑 Wajib Top 3 Sektor", value=True)
    anti_correlation = st.toggle("🕸️ Anti-Korelasi", value=True, help="Maksimal 1 saham per sektor untuk mencegah kebangkrutan massal.")
    bypass_lockdown = st.toggle("🚨 Bypass Market Lockdown", value=False, help="Paksa scan meskipun IHSG sedang hancur.")
    
    st.divider()
    st.header("⚙️ Capital & Risk")
    capital = st.number_input("Portfolio (Rp)", value=5000000, step=1000000)
    risk_pct = st.slider("Max Loss Per Trade (%)", 0.5, 5.0, 2.0, step=0.5)

# --- EXECUTION ENGINE ---
if st.button("🚀 ENGAGE QUANTITATIVE SCAN", use_container_width=True, type="primary"):
    # FITUR 1: MARKET BREADTH LOCKDOWN
    market_health, ihsg_price = get_market_health()
    
    if market_health == "BEARISH" and not bypass_lockdown:
        st.markdown(f"""
        <div class='lockdown-box'>
            <h2 style='margin:0;'>⛔ MARKET LOCKDOWN AKTIF</h2>
            <p>IHSG berada di bawah MA-50 (Bearish / Sedang Hancur). Algoritma menolak memberikan rekomendasi *Buy* untuk melindungi modal Anda. <i>Cash is King</i>.<br>
            (Gunakan tombol Bypass di Sidebar jika Anda memaksa ingin *trading* melawan tren pasar).</p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
        
    with st.status(f"Market Status: {market_health}. Membaca Aliran Uang...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia')
                 .select('name','close','volume','sector','Perf.1M','market_cap_basic')
                 .where(Column('market_cap_basic') >= 1e11))
            _, df_raw = q.get_scanner_data()
            
            if not df_raw.empty:
                df_raw = df_raw.dropna(subset=['sector', 'Perf.1M'])
                sector_perf = df_raw.groupby('sector')['Perf.1M'].mean().sort_values(ascending=False)
                top_3_sectors = sector_perf.head(3).index.tolist()
                
                st.write("### 🏆 Top 3 Sektor Pembawa Uang:")
                for i, sec in enumerate(top_3_sectors):
                    st.success(f"{i+1}. **{sec}** (+{sector_perf[sec]:.2f}%)")
                
                df_scan = df_raw[df_raw['sector'].isin(top_3_sectors)] if strict_sector else df_raw
                
                pesan_tele = f"🌍 <b>V44.0 HEDGE FUND REPORT</b>\n"
                valid_stocks = []
                used_sectors = [] # Untuk Anti-Korelasi
                
                for idx, row in df_scan.iterrows():
                    if len(valid_stocks) >= 3: break 
                    
                    t_sym = row['name']
                    t_sector = row['sector']
                    
                    # FITUR 2: ANTI-KORELASI
                    if anti_correlation and t_sector in used_sectors:
                        continue 
                    
                    time.sleep(1.2) 
                    df_hist = yf.Ticker(f"{t_sym}.JK").history(period="1y")
                    
                    if not df_hist.empty and check_minervini_template(df_hist):
                        is_profit, eps, _, turnover = check_fundamentals(t_sym, df_hist)
                        
                        if not is_profit: continue
                        
                        if detect_squeeze(df_hist) and check_smart_money(df_hist):
                            atr = calculate_atr(df_hist)
                            lp = float(row['close'])
                            sma20 = df_hist['Close'].rolling(20).mean().iloc[-1]
                            
                            # FITUR 3: QUICK BACKTEST WIN RATE
                            win_rate, triggers = quick_backtest(df_hist)
                            
                            trigger_price = int(max(sma20, lp))
                            sl_price = int(trigger_price - (atr * 2.0)) 
                            target_price = int(trigger_price + (atr * 4.0)) 
                            ts_dist = atr * 2.5
                            ts_pct = round((ts_dist / trigger_price) * 100, 1)
                            
                            risk_rp = trigger_price - sl_price
                            rrr = round((target_price - trigger_price) / risk_rp, 1) if risk_rp > 0 else 0
                            
                            if rrr < 2.0: continue 
                            
                            lot = int(((capital * (risk_pct/100)) / risk_rp) / 100) if risk_rp > 0 else 0
                            if lot == 0: continue
                            
                            # Catat Sektor yang sudah terpakai
                            used_sectors.append(t_sector)
                            
                            turnover_m = turnover / 1_000_000_000
                            rank_sektor = top_3_sectors.index(t_sector) + 1 if t_sector in top_3_sectors else "Lainnya"
                            
                            # Rekam ke Jurnal
                            valid_stocks.append({
                                "Saham": t_sym, "Sektor": t_sector, "Trigger": trigger_price,
                                "Lot": lot, "SL": sl_price, "TP": target_price, "TS_Pct": ts_pct, "WinRate_%": win_rate
                            })
                            
                            # TAMPILAN MATRIKS
                            html_card = f"""
                            <div class='stock-card'>
                                <h2 style='margin:0;'>{t_sym} <span class='sector-badge'>SEKTOR RANK #{rank_sektor}</span></h2>
                                <p style='color:#a1a1aa; font-size:14px; margin:0 0 10px 0;'>Sektor: <b>{t_sector}</b> | Win Rate Historis: <b>{win_rate}%</b> ({triggers}x Squeeze)</p>
                                
                                <div style='background-color:#0d1117; padding:15px; border-radius:8px; border:1px solid #30363d; margin-top:10px;'>
                                    <p style='margin:0 0 5px 0; color:#d4d4d8; font-weight:bold; font-size:12px; text-transform:uppercase;'>The Top-Down Matrix:</p>
                                    <ul style='margin:0; padding-left:20px; font-size:14px; color:#8b5cf6; line-height:1.6;'>
                                        <li><b>Macro Context:</b> {'Market Health Valid.' if market_health == 'BULLISH' else 'Bypass Lockdown Aktif.'}</li>
                                        <li><b>Anti-Korelasi:</b> 1 Saham Terkuat dari Sektor {t_sector}.</li>
                                        <li><b>Backtest:</b> Algoritma berhasil memprediksi {win_rate}% kenaikan pasca-Squeeze dalam 1 tahun terakhir.</li>
                                    </ul>
                                </div>
                                
                                <div style='background-color:#1e1b4b; border-left:4px solid #8b5cf6; padding:12px; margin-top:15px; border-radius:4px;'>
                                    <p style='margin:0; font-size:13px; color:#c4b5fd;'>
                                        <b>🚨 SOP HIBRIDA:</b> Beli <b>{lot} Lot</b> di <b>Rp {trigger_price}</b>. 
                                        Jual 50% di <b>Rp {target_price}</b>. Kawal 50% dengan TS <b>{ts_pct}%</b>.
                                    </p>
                                </div>
                            </div>
                            """
                            st.markdown(html_card, unsafe_allow_html=True)
                            
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("🎯 TRIGGER PRICE", f"Rp {trigger_price}")
                            c2.metric("🛡️ STOP LOSS", f"Rp {sl_price}")
                            c3.metric("💰 TP (50%)", f"Rp {target_price}")
                            c4.metric("📈 TRAILING (50%)", f"{ts_pct}%")
                            
                            pesan_tele += f"\n🌍 <b>{t_sym} ({t_sector})</b>\n"
                            pesan_tele += f"🚨 <b>{lot} Lot @ Rp {trigger_price}</b>\n"
                            pesan_tele += f"🛡️ SL: Rp {sl_price} | TP: Rp {target_price}\n"
                            pesan_tele += f"📈 Hold Sisa: TS {ts_pct}%\n"
                            pesan_tele += f"🧪 Hist. Win Rate: {win_rate}%\n"

                if len(valid_stocks) > 0 and send_telegram:
                    requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", data={"chat_id": TELE_CHAT_ID, "text": pesan_tele, "parse_mode": "HTML"})
                
                status.update(label=f"Scan & Backtest Selesai!", state="complete", expanded=False)
                
                if len(valid_stocks) == 0: 
                    st.warning("Mesin tidak menemukan setup yang lolos semua filter Institusi hari ini.")
                else:
                    # FITUR 4: JURNAL TRADING (DOWNLOAD CSV)
                    st.divider()
                    df_jurnal = pd.DataFrame(valid_stocks)
                    csv = df_jurnal.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Jurnal Trading (CSV)",
                        data=csv,
                        file_name=f"Jurnal_V44_{pd.Timestamp.now().strftime('%Y-%m-%d')}.csv",
                        mime="text/csv",
                    )
            else: st.error("Gagal menarik data sektor dari pasar.")
        except Exception as e:
            st.error(f"Engine Error: {e}")