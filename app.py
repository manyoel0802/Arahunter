import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import time # Protokol Anti-Rate Limit
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(page_title="GLOBAL ORACLE V50.1", layout="wide", page_icon="🌎")

st.markdown("""
    <style>
    .main { background-color: #09090b; }
    .stMetric { background-color: #18181b; border: 1px solid #27272a; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #3f3f46; color: white; }
    .bg-global { background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 50%, #1e1b4b 100%); border-top: 5px solid #6366f1; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3); }
    .asset-card { background-color: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #6366f1; }
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
        df['Band_Width'] = ((df['SMA20'] + (df['STD20'] * 2)) - (df['SMA20'] - (df['STD20'] * 2))) / df['SMA20']
        return df['Band_Width'].iloc[-1] <= (df['Band_Width'].tail(20).min() * 1.15) 
    except: return False

def check_trend(df, mode="CRYPTO"):
    try:
        c = df['Close'].iloc[-1]
        if mode == "CRYPTO":
            sma20 = df['Close'].rolling(20).mean().iloc[-1]
            sma50 = df['Close'].rolling(50).mean().iloc[-1]
            return "BULLISH" if (c > sma20 and sma20 > sma50) else "SIDEWAYS"
        else: # FOREX/GOLD
            ema50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            ema200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
            if c > ema50 and ema50 > ema200: return "BULLISH"
            elif c < ema50 and ema50 < ema200: return "BEARISH"
            return "SIDEWAYS"
    except: return "SIDEWAYS"

# --- UI HEADER ---
st.markdown("""
<div class='status-card bg-global'>
    <h1 style='margin:0; color:#f0f9ff;'>🌎 GLOBAL ORACLE V50.1</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#c7d2fe;'>
        Multi-Asset Engine: Crypto, Forex, & Gold | Anti-Rate Limit Protocol Active
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ COMMAND CENTER ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    market_type = st.radio("Pilih Market:", ["CRYPTO (USD)", "FOREX & GOLD"])
    capital = st.number_input("Modal Trading (USD)", value=1000, step=100)
    risk_pct = st.slider("Max Loss Per Trade (%)", 0.5, 5.0, 1.0, step=0.5)
    
    st.divider()
    st.info("💡 **Anti-Rate Limit:** Sistem akan memberikan jeda 1.5 detik antar aset untuk menghindari pemblokiran server.")

# --- ASSET LISTS ---
crypto_list = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'AVAX-USD', 'LINK-USD', 'NEAR-USD']
fx_pairs = {
    'XAUUSD=X': ('GOLD', 100),
    'EURUSD=X': ('EUR/USD', 100000),
    'GBPUSD=X': ('GBP/USD', 100000),
    'USDJPY=X': ('USD/JPY', 100000),
    'AUDUSD=X': ('AUD/USD', 100000)
}

# --- EXECUTION ---
if st.button(f"🚀 SCAN {market_type}", use_container_width=True, type="primary"):
    with st.status(f"Scanning {market_type} Assets...", expanded=True) as status:
        try:
            valid_setups = 0
            assets = crypto_list if market_type == "CRYPTO (USD)" else fx_pairs.keys()
            
            for symbol in assets:
                st.write(f"🔍 Memeriksa {symbol}...")
                
                # PROTOKOL ANTI-RATE LIMIT
                time.sleep(1.5) 
                
                ticker = yf.Ticker(symbol)
                df_hist = ticker.history(period="1y")
                
                if df_hist.empty:
                    st.warning(f"Data {symbol} tidak ditemukan atau limit tercapai.")
                    continue
                
                mode = "CRYPTO" if market_type == "CRYPTO (USD)" else "FOREX"
                trend = check_trend(df_hist, mode=mode)
                
                if trend == "SIDEWAYS": continue
                
                if detect_squeeze(df_hist):
                    atr = calculate_atr(df_hist)
                    lp = float(df_hist['Close'].iloc[-1])
                    sma20 = float(df_hist['Close'].rolling(20).mean().iloc[-1])
                    
                    # Logic Setup
                    if trend == "BULLISH":
                        trigger = max(sma20, lp)
                        sl = trigger - (atr *