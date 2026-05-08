import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import time

# --- 🚀 ENTERPRISE CONFIGURATION ---
st.set_page_config(page_title="FX ORACLE V70.0", layout="wide", page_icon="👑")

st.markdown("""
    <style>
    .main { background-color: #020617; }
    .stMetric { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #1e293b; color: white; }
    .bg-godmode { background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 50%, #450a0a 100%); border-bottom: 4px solid #ef4444; }
    .card-signal { background-color: #1e293b; border-left: 5px solid #ef4444; padding: 20px; border-radius: 8px; margin-bottom: 15px; }
    .lock-box { background: #1e1b4b; border: 1px solid #4338ca; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 🧠 QUANTITATIVE ENGINE (THE PERFECT CORE) ---
class ForexEngineV70:
    @staticmethod
    def get_indicators(df):
        try:
            df = df.copy()
            # 1. Trend (EMA)
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
            
            # 2. Volatility Squeeze (Bollinger Bands)
            df['SMA20'] = df['Close'].rolling(window=20).mean()
            df['STD20'] = df['Close'].rolling(window=20).std()
            df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
            df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
            df['BW'] = (df['Upper'] - df['Lower']) / df['SMA20']
            
            # 3. Momentum Validator (RSI-14)
            delta = df['Close'].diff()
            gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
            loss = -1 * delta.clip(upper=0).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 4. Risk Management (ATR)
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(window=14).mean()
            
            return df
        except Exception as e:
            return df

    @staticmethod
    def check_setup(df):
        if df is None or len(df) < 200: return None, 0
        curr = df.iloc[-1]
        prev_bw_min = df['BW'].tail(20).min()
        
        # Matrix Conditions
        is_uptrend = curr['Close'] > curr['EMA50'] > curr['EMA200']
        is_downtrend = curr['Close'] < curr['EMA50'] < curr['EMA200']
        is_squeeze = curr['BW'] <= (prev_bw_min * 1.15)
        
        # Momentum Conditions (Filter Sinyal Palsu)
        strong_bull = curr['RSI'] > 55
        strong_bear = curr['RSI'] < 45
        
        if is_squeeze:
            if is_uptrend and strong_bull: return "STRONG BUY", curr['RSI']
            if is_downtrend and strong_bear: return "STRONG SELL", curr['RSI']
        return None, curr['RSI']

# --- 👑 UI: COMMAND CENTER ---
st.markdown("""
<div class='status-card bg-godmode'>
    <h1 style='margin:0;'>👑 THE PERFECT FX ORACLE V70.0</h1>
    <p style='margin:5px 0 0 0; opacity:0.9;'>Trend + Volatility + Momentum + Macro Protocol</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⏱️ Radar Settings")
    timeframe = st.radio("Timeframe (Kecepatan)", ["1 Hour (H1) - Intraday", "1 Day (D1) - Swing Trade"])
    
    st.divider()
    st.header("💰 Risk Parameter")
    balance = st.number_input("MT4/MT5 Balance ($)", value=1000, step=100)
    risk_per_trade = st.slider("Risk Per Trade (%)", 0.5, 2.0, 1.0, step=0.5)

# --- 🔒 MACRO NEWS PROTOCOL ---
st.markdown("""
<div class='lock-box'>
    <h3 style='margin:0; color:#818cf8;'>🛡️ Pre-Flight Macro Checklist</h3>
    <p style='font-size:14px; color:#a5b4fc;'>Sistem menolak untuk memindai pasar jika Kapten belum mengecek jadwal berita ekonomi harian (ForexFactory / Investing.com).</p>
</div>
""", unsafe_allow_html=True)

news_cleared = st.checkbox("✅ Saya konfirmasi: TIDAK ADA berita High-Impact (Merah) dari USD dalam 4 jam ke depan.")

# --- 🛰️ ASSET UNIVERSE ---
fx_assets = ['XAUUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X']

# --- 🚀 EXECUTION ---
# Tombol hanya bisa ditekan jika checkbox berita makro sudah dicentang!
if st.button("ENGAGE QUANTITATIVE SCAN", use_container_width=True, type="primary", disabled=not news_cleared):
    with st.status(f"Scanning {timeframe} Liquidity...", expanded=True) as status:
        results = []
        
        # Konfigurasi Timeframe Yahoo Finance
        interval_yf = "1h" if "H1" in timeframe else "1d"
        period_yf = "730d" if "H1" in timeframe else "2y" # 730 hari adalah batas maksimal data 1 jam di yfinance
        
        for symbol in fx_assets:
            try:
                st.write(f"📡 Downloading {symbol} ({interval_yf})...")
                time.sleep(1.5) # Anti-Rate Limit Tetap Aktif
                
                ticker_obj = yf.Ticker(symbol)
                df_raw = ticker_obj.history(period=period_yf, interval=interval_yf) 
                
                if df_raw.empty: continue
                
                df = ForexEngineV70.get_indicators(df_raw)
                signal, rsi_val = ForexEngineV70.check_setup(df)
                
                if signal:
                    curr = df.iloc[-1]
                    atr = curr['ATR']
                    price = curr['Close']
                    
                    # Risk Distance (2.5x ATR)
                    sl_dist = atr * 2.5
                    if "BUY" in signal:
                        sl = price - sl_dist
                        tp = price + (sl_dist * 2.5) # RRR 1:2.5
                    else:
                        sl = price + sl_dist
                        tp = price - (sl_dist * 2.5)
                    
                    # MetaTrader Sizing Engine
                    risk_val = balance * (risk_per_trade / 100)
                    contract = 100 if "XAU" in symbol else 100000
                    
                    if "JPY" in symbol:
                        size = risk_val / (sl_dist * (100000 / price))
                    else:
                        size = risk_val / (sl_dist * contract)
                        
                    size = round(max(0.01, size), 2)

                    results.append({
                        "Symbol": symbol.replace('=X', ''), "Signal": signal, "Price": price,
                        "SL": sl, "TP": tp, "Size": size, "RSI": rsi_val
                    })
            except Exception as e:
                st.warning(f"Data error pada {symbol}: {e}")

        # --- 📊 OUTPUT DISPLAY ---
        if results:
            status.update(label="Scanning Selesai!", state="complete")
            for res in results:
                color = "#10b981" if "BUY" in res['Signal'] else "#ef4444"
                icon = "🥇" if "XAU" in res['Symbol'] else "💱"
                
                st.markdown(f"""
                <div class='card-signal' style='border-left: 5px solid {color};'>
                    <h3 style='margin:0; color:{color};'>{icon} {res['Signal']} | {res['Symbol']}</h3>
                    <p style='color:#94a3b8; font-size:14px;'>
                        Momentum Terkonfirmasi (RSI: <b>{res['RSI']:.1f}</b>). Makro Terkunci Aman.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("ENTRY POINT", f"{res['Price']:.5f}")
                c2.metric("STOP LOSS", f"{res['SL']:.5f}")
                c3.metric("TAKE PROFIT", f"{res['TP']:.5f}")
                c4.metric("MT4 LOT SIZE", f"{res['Size']} Lot")
        else:
            status.update(label="Tidak ada setup sempurna hari ini.", state="complete")
            st.info(f"Market di timeframe {interval_yf} sedang tidak memiliki kombinasi Tren, Squeeze, dan Momentum yang sinkron. Disiplin adalah profit yang tertunda.")