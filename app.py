import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import time

# --- 🚀 ENTERPRISE CONFIGURATION ---
st.set_page_config(page_title="OMNI-ORACLE V60.1", layout="wide", page_icon="🏛️")

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
            # Menggunakan salinan data agar tidak merusak dataframe asli
            df = df.copy()
            # Moving Averages
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['SMA20'] = df['Close'].rolling(window=20).mean()
            # Volatility Squeeze
            df['STD20'] = df['Close'].rolling(window=20).std()
            df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
            df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
            df['BW'] = (df['Upper'] - df['Lower']) / df['SMA20']
            # ATR for Risk Management
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(window=14).mean()
            return df
        except Exception as e:
            st.error(f"Kalkulasi Indikator Gagal: {e}")
            return df

    @staticmethod
    def check_setup(df, market_type):
        if df is None or len(df) < 200: return None
        curr = df.iloc[-1]
        # Cari nilai minimum Bandwidth dalam 20 hari terakhir
        prev_bw_min = df['BW'].tail(20).min()
        
        # Konfirmasi Trend & Squeeze
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
    <h1 style='margin:0;'>🏛️ OMNI-ORACLE SYSTEM V60.1</h1>
    <p style='margin:5px 0 0 0; opacity:0.8;'>Institutional Multi-Asset Terminal | Anti-Crash Edition</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🕹️ Terminal Control")
    m_type = st.selectbox("Market Universe", ["IHSG STOCKS", "CRYPTO (USDT)", "FOREX & GOLD"])
    
    st.divider()
    st.header("💰 Capital Allocation")
    curr_label = "IDR" if m_type == "IHSG STOCKS" else "USD"
    balance = st.number_input(f"Portfolio Balance ({curr_label})", value=10000000 if m_type == "IHSG STOCKS" else 1000)
    risk_per_trade = st.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0)

# --- 🛰️ ASSET UNIVERSE ---
universes = {
    "IHSG STOCKS": ['BBCA.JK', 'BMRI.JK', 'BBRI.JK', 'TLKM.JK', 'ASII.JK', 'BBNI.JK', 'ADRO.JK', 'GOTO.JK', 'AMRT.JK', 'PANI.JK'],
    "CRYPTO (USDT)": ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'AVAX-USD', 'NEAR-USD', 'LINK-USD'],
    "FOREX & GOLD": ['XAUUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']
}

# --- 🚀 EXECUTION ---
if st.button(f"RUN STABLE SCAN: {m_type}", use_container_width=True, type="primary"):
    with st.status(f"Scanning {m_type} Assets...", expanded=True) as status:
        results = []
        assets = universes[m_type]
        
        for symbol in assets:
            try:
                st.write(f"📡 Downloading {symbol}...")
                time.sleep(1.5) # Jeda agar tidak kena Rate Limit
                
                # PERBAIKAN: Menggunakan .Ticker().history() alih-alih .download()
                ticker_obj = yf.Ticker(symbol)
                df_raw = ticker_obj.history(period="2y") # Ambil 2 tahun untuk SMA200
                
                if df_raw.empty: continue
                
                df = OmniEngine.get_indicators(df_raw)
                signal = OmniEngine.check_setup(df, m_type)
                
                if signal:
                    curr = df.iloc[-1]
                    atr = curr['ATR']
                    price = curr['Close']
                    
                    # Risk Distance (2.5x ATR)
                    sl_dist = atr * 2.5
                    sl = (price - sl_dist) if signal == "BULLISH" else (price + sl_dist)
                    tp = (price + (sl_dist * 2.5)) if signal == "BULLISH" else (price - (sl_dist * 2.5))
                    
                    # Size Engine
                    risk_val = balance * (risk_per_trade / 100)
                    if m_type == "IHSG STOCKS":
                        size = int(risk_val / (sl_dist * 100)) # Satuan Lot
                        unit = "Lot"
                    elif m_type == "CRYPTO (USDT)":
                        size = risk_val / sl_dist
                        unit = "Unit"
                    else:
                        contract = 100 if "XAU" in symbol else 100000
                        size = round(risk_val / (sl_dist * contract), 2) if "JPY" not in symbol else round(risk_val / (sl_dist * (100000/price)), 2)
                        unit = "Std Lot"

                    results.append({
                        "Symbol": symbol, "Signal": signal, "Price": price,
                        "SL": sl, "TP": tp, "Size": size, "Unit": unit
                    })
            except Exception as e:
                st.warning(f"Aset {symbol} dilewati karena kendala data: {e}")

        # --- 📊 OUTPUT DISPLAY ---
        if results:
            status.update(label="Scanning Selesai!", state="complete")
            for res in results:
                color = "#10b981" if res['Signal'] == "BULLISH" else "#ef4444"
                st.markdown(f"""
                <div class='card-signal'>
                    <h3 style='margin:0; color:{color};'>{res['Signal']} | {res['Symbol']}</h3>
                    <p style='color:#94a3b8; font-size:14px;'>Action: Pasang Order Pending di {res['Price']:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("ENTRY", f"{res['Price']:.2f}")
                c2.metric("STOP LOSS", f"{res['SL']:.2f}")
                c3.metric("TAKE PROFIT", f"{res['TP']:.2f}")
                c4.metric("SIZE", f"{res['Size']} {res['Unit']}")
        else:
            status.update(label="Tidak ada sinyal hari ini.", state="complete")
            st.info("Market sedang tidak memberikan setup ideal. Sabar adalah kunci, Kapten.")