import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="FX ORACLE V50.0", layout="wide", page_icon="🥇")

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0f172a; }
    .stMetric { background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #334155; color: white; }
    .bg-forex { background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 50%, #312e81 100%); border-top: 5px solid #818cf8; box-shadow: 0 4px 20px rgba(129, 140, 248, 0.3); }
    .fx-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #fbbf24; }
    .badge-gold { background-color: #fbbf24; color: #451a03; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .badge-fx { background-color: #818cf8; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 🥇 QUANTITATIVE ENGINES ---
def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def detect_squeeze(df):
    try:
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Band_Width'] = ((df['SMA20'] + (df['STD20'] * 2)) - (df['SMA20'] - (df['STD20'] * 2))) / df['SMA20']
        return df['Band_Width'].iloc[-1] <= (df['Band_Width'].tail(20).min() * 1.15) 
    except: return False

def check_trend_alignment(df):
    try:
        # Forex butuh konfirmasi trend yang solid (EMA 50 & EMA 200)
        c = df['Close'].iloc[-1]
        ema50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
        
        if c > ema50 and ema50 > ema200: return "BULLISH"
        elif c < ema50 and ema50 < ema200: return "BEARISH"
        else: return "SIDEWAYS"
    except: return "SIDEWAYS"

# --- UI HEADER ---
st.markdown("""
<div class='status-card bg-forex'>
    <h1 style='margin:0; color:#e0e7ff;'>🥇 GOD MODE V50.0: FX & GOLD ORACLE</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#a5b4fc;'>
        Institutional MetaTrader 4/5 Signal Generator | Volatility Breakout & Trend Alignment
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Risk Management (MT4/MT5)")
    capital_usd = st.number_input("Balance Akun (USD)", value=1000, step=100)
    risk_pct = st.slider("Max Loss Per Trade (%)", 0.5, 5.0, 1.0, step=0.5)
    
    st.divider()
    st.header("🛡️ Tactical Filters")
    min_rrr = st.number_input("Target RRR Minimal (x)", value=2.0, step=0.5)

# --- EXECUTION ENGINE ---
if st.button("🚀 SCAN MAJOR PAIRS & GOLD", use_container_width=True, type="primary"):
    with st.status("Memindai Server Likuiditas Antar Bank...", expanded=True) as status:
        try:
            # Pair Utama dengan Likuiditas Tertinggi di Dunia
            fx_pairs = {
                'XAUUSD=X': ('GOLD (Emas)', 100),       # Contract Size 100 oz per 1 Lot Standard
                'EURUSD=X': ('Euro / US Dollar', 100000), # Contract Size 100,000 per 1 Lot Standard
                'GBPUSD=X': ('British Pound / USD', 100000),
                'USDJPY=X': ('US Dollar / Yen', 100000),
                'AUDUSD=X': ('Aussie / USD', 100000)
            }
            
            valid_setups = 0
            
            for symbol, (name, contract_size) in fx_pairs.items():
                df_hist = yf.Ticker(symbol).history(period="1y")
                
                if df_hist.empty: continue
                
                trend = check_trend_alignment(df_hist)
                if trend == "SIDEWAYS": continue # Lewati pasar yang sedang bingung
                
                if detect_squeeze(df_hist):
                    atr = calculate_atr(df_hist)
                    lp = float(df_hist['Close'].iloc[-1])
                    sma20 = float(df_hist['Close'].rolling(20).mean().iloc[-1])
                    
                    # LOGIKA LONG (BULLISH) ATAU SHORT (BEARISH)
                    if trend == "BULLISH":
                        trigger_price = max(sma20, lp)
                        sl_price = trigger_price - (atr * 2.0)
                        target_price = trigger_price + (atr * 4.0)
                        risk_distance = trigger_price - sl_price
                        action = "BUY LIMIT / BUY STOP"
                        color_theme = "#10b981"
                    else:
                        trigger_price = min(sma20, lp)
                        sl_price = trigger_price + (atr * 2.0)
                        target_price = trigger_price - (atr * 4.0)
                        risk_distance = sl_price - trigger_price
                        action = "SELL LIMIT / SELL STOP"
                        color_theme = "#ef4444"
                    
                    rrr = round(abs(target_price - trigger_price) / risk_distance, 1) if risk_distance > 0 else 0
                    
                    if rrr < min_rrr: continue 
                    
                    # --- PERHITUNGAN LOT SIZE METATRADER OTOMATIS ---
                    max_loss_usd = capital_usd * (risk_pct/100)
                    
                    # Rumus MT4: Lot = Risk USD / (Jarak Pips * Nilai Pip) -> Disederhanakan pakai Contract Size
                    if "JPY" in symbol:
                        # Khusus JPY pair, hitungannya berbeda karena nilai tukarnya di angka ratusan
                        pip_value_estimate = 100000 / lp
                        lot_size = max_loss_usd / (risk_distance * pip_value_estimate)
                    else:
                        lot_size = max_loss_usd / (risk_distance * contract_size)
                    
                    lot_size = round(max(0.01, min(lot_size, 50.0)), 2) # Dibulatkan ke Lot Micro (0.01)
                    
                    valid_setups += 1
                    
                    badge = "<span class='badge-gold'>GOLD</span>" if "XAU" in symbol else "<span class='badge-fx'>MAJOR FX</span>"
                    
                    html_card = f"""
                    <div class='fx-card'>
                        <h2 style='margin:0; color:{color_theme};'>{symbol.replace('=X', '')} {badge}</h2>
                        <p style='color:#94a3b8; font-size:14px; margin:0 0 10px 0;'>Aset: <b>{name}</b> | Trend Utama: <b>{trend}</b></p>
                        <div style='background-color:#0f172a; padding:15px; border-radius:8px; border:1px solid #334155;'>
                            <ul style='margin:0; padding-left:20px; font-size:14px; color:#cbd5e1; line-height:1.6;'>
                                <li><b>Peluang:</b> Volatilitas harga sedang sangat terjepit (Bollinger Squeeze).</li>
                                <li><b>Instruksi MT4/MT5:</b> Buka aplikasi MetaTrader Anda, pilih <b>New Order</b>. Atur Lot sesuai rekomendasi, lalu pasang Pending Order.</li>
                            </ul>
                        </div>
                    </div>
                    """
                    st.markdown(html_card, unsafe_allow_html=True)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"🎯 AKSI: {action}", f"{trigger_price:.5f}")
                    c2.metric("🛡️ STOP LOSS", f"{sl_price:.5f}")
                    c3.metric("💰 TAKE PROFIT", f"{target_price:.5f}")
                    c4.metric("📦 LOT SIZE (MT4)", f"{lot_size} Lot")

            status.update(label=f"Scan Forex & Gold Selesai!", state="complete", expanded=False)
            if valid_setups == 0: st.warning("Semua aset utama sedang tidak berada dalam fase ledakan. Mesin menyarankan Anda untuk beristirahat hari ini.")
        except Exception as e:
            st.error(f"Engine Error: {e}")