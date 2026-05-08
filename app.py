import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import time
import datetime

# --- 🚀 ENTERPRISE CONFIGURATION ---
st.set_page_config(page_title="OMNI-ORACLE V60.0", layout="wide", page_icon="🏛️")

# Custom CSS for Professional Dark Theme
st.markdown("""
    <style>
    .main { background-color: #020617; }
    .stMetric { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #1e293b; color: white; }
    .bg-omni { background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-bottom: 4px solid #6366f1; }
    .card-signal { background-color: #1e293b; border-left: 5px solid #6366f1; padding: 20px; border-radius: 8px; margin-bottom: 15px; }
    .warning-box { background-color: #450a0a; border: 1px solid #991b1b; color: #fca5a5; padding: 15px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 🧠 CORE QUANTITATIVE ENGINE ---
class OmniEngine:
    @staticmethod
    def get_indicators(df):
        try:
            # Trend
            df['SMA50'] = df['Close'].rolling(50).mean()
            df['SMA200'] = df['Close'].rolling(200).mean()
            # Volatility Squeeze
            df['SMA20'] = df['Close'].rolling(20).mean()
            df['STD20'] = df['Close'].rolling(20).std()
            df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
            df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
            df['BW'] = (df['Upper'] - df['Lower']) / df['SMA20']
            # ATR for Risk
            tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
            df['ATR'] = tr.rolling(14).mean()
            return df
        except: return df

    @staticmethod
    def check_setup(df, market_type):
        if len(df) < 200: return None
        curr = df.iloc[-1]
        prev_bw_min = df['BW'].tail(20).min()
        
        # Logic: Trend + Squeeze
        is_uptrend = curr['Close'] > curr['SMA50'] > curr['SMA200']
        is_downtrend = curr['Close'] < curr['SMA50'] < curr['SMA200']
        is_squeeze = curr['BW'] <= (prev_bw_min * 1.15)
        
        if is_squeeze:
            if is_uptrend: return "BULLISH"
            if is_downtrend and market_type != "IHSG STOCKS": return "BEARISH"
        return None

# --- 🏛️ UI: COMMAND CENTER ---
st.markdown("""
<div class='status-card bg-omni'>
    <h1 style='margin:0;'>🏛️ OMNI-ORACLE SYSTEM V60.0</h1>
    <p style='margin:5px 0 0 0; opacity:0.8;'>Institutional Multi-Asset Quantitative Terminal</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🕹️ Terminal Control")
    m_type = st.selectbox("Market Universe", ["IHSG STOCKS", "CRYPTO (USDT)", "FOREX & GOLD"])
    
    st.divider()
    st.header("💰 Capital Allocation")
    balance = st.number_input("Portfolio Balance (USD/IDR)", value=10000000 if m_type == "IHSG STOCKS" else 1000)
    risk_per_trade = st.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0)
    
    st.divider()
    st.header("🔑 API Connection")
    api_key = st.text_input("Professional API Key (Optional)", type="password", help="Gunakan TwelveData atau GoAPI untuk Skor 10/10")

# --- 🛰️ ASSET UNIVERSE ---
universes = {
    "IHSG STOCKS": ['BBCA.JK', 'BMRI.JK', 'BBRI.JK', 'TLKM.JK', 'ASII.JK', 'BBNI.JK', 'ADRO.JK', 'GOTO.JK', 'AMRT.JK', 'PANI.JK'],
    "CRYPTO (USDT)": ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'AVAX-USD', 'NEAR-USD', 'LINK-USD', 'RENDER-USD'],
    "FOREX & GOLD": ['XAUUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']
}

# --- 🚀 EXECUTION ---
if st.button(f"RUN QUANTITATIVE SCAN: {m_type}", use_container_width=True, type="primary"):
    with st.status(f"Processing {m_type} Architecture...", expanded=True) as status:
        results = []
        assets = universes[m_type]
        
        for symbol in assets:
            try:
                st.write(f"📡 Analyzing {symbol}...")
                time.sleep(1.2) # Hardened Anti-Rate Limit
                
                raw_data = yf.download(symbol, period="1y", interval="1d", progress=False)
                if raw_data.empty: continue
                
                df = OmniEngine.get_indicators(raw_data)
                signal = OmniEngine.check_setup(df, m_type)
                
                if signal:
                    curr = df.iloc[-1]
                    atr = curr['ATR']
                    price = curr['Close']
                    
                    # Risk Calculation
                    sl_dist = atr * 2.5
                    sl = (price - sl_dist) if signal == "BULLISH" else (price + sl_dist)
                    tp = (price + (sl_dist * 2)) if signal == "BULLISH" else (price - (sl_dist * 2))
                    
                    # Size Engine
                    risk_amount = balance * (risk_per_trade / 100)
                    if m_type == "IHSG STOCKS":
                        size = int((risk_amount / (sl_dist * 100))) # Convert to Lots
                        unit = "Lot"
                    elif m_type == "CRYPTO (USDT)":
                        size = risk_amount / sl_dist
                        unit = "Unit"
                    else:
                        size = round(risk_amount / (sl_dist * 100000), 2) if "JPY" not in symbol else round(risk_amount / (sl_dist * (100000/price)), 2)
                        unit = "Standard Lot"

                    results.append({
                        "Symbol": symbol, "Signal": signal, "Price": price,
                        "SL": sl, "TP": tp, "Size": size, "Unit": unit
                    })
            except Exception as e:
                st.error(f"Hardware Fault on {symbol}: {e}")

        # --- 📊 OUTPUT DISPLAY ---
        if results:
            status.update(label="Analysis Complete. Signals Found!", state="complete")
            
            # Exposure Check (Correlation Filter)
            if len(results) > 2:
                st.markdown(f"""
                <div class='warning-box'>
                    ⚠️ <b>HIGH EXPOSURE WARNING:</b> Ditemukan {len(results)} sinyal bersamaan. 
                    Pastikan korelasi antar aset tidak terlalu tinggi untuk menghindari Margin Call massal.
                </div>
                """, unsafe_allow_html=True)

            for res in results:
                with st.container():
                    color = "#10b981" if res['Signal'] == "BULLISH" else "#ef4444"
                    st.markdown(f"""
                    <div class='card-signal'>
                        <h3 style='margin:0; color:{color};'>{res['Signal']} | {res['Symbol']}</h3>
                        <p style='color:#94a3b8; font-size:14px;'>SOP: Entry {res['Price']:.2f} | RRR 1:2 Ready</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("ENTRY", f"{res['Price']:.2f}")
                    c2.metric("STOP LOSS", f"{res['SL']:.2f}")
                    c3.metric("TAKE PROFIT", f"{res['TP']:.2f}")
                    c4.metric("POSITION SIZE", f"{res['Size']} {res['Unit']}")
        else:
            status.update(label="Scanning Finished. No Setup Found.", state="complete")
            st.info("Sistem tetap dalam mode siaga. Tidak ada setup yang memenuhi standar institusi hari ini.")