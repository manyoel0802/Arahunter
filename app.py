import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings
from tradingview_screener import Query, Column

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V41.1", layout="wide", page_icon="🏹")

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; color: white; border: 1px solid #30363d; }
    .bg-breakout { background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%); border-top: 5px solid #6366f1; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4); }
    .stock-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #6366f1; }
    .indicator-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 5px; margin-bottom: 5px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 🏹 BREAKOUT ENGINES ---
def check_fundamentals(ticker):
    try:
        info = yf.Ticker(f"{ticker}.JK").info
        eps = info.get('trailingEps', 0) or 0
        return eps > 0, round(eps, 1)
    except: return True, 0

def detect_breakout(ticker):
    try:
        # Ambil data harian untuk melihat pola breakout
        df = yf.Ticker(f"{ticker}.JK").history(period="1mo")
        if len(df) < 20: return None
        
        lp = df['Close'].iloc[-1]
        prev_high = df['High'].iloc[-21:-1].max() # High 20 hari terakhir
        
        # 1. Price Breakout
        is_breakout = lp > prev_high
        
        # 2. Volume Confirmation
        avg_vol = df['Volume'].iloc[-21:-1].mean()
        is_vol_pump = df['Volume'].iloc[-1] > (avg_vol * 1.5)
        
        # 3. Momentum RSI
        close_delta = df['Close'].diff()
        up = close_delta.clip(lower=0).rolling(14).mean()
        down = (-1 * close_delta.clip(upper=0)).rolling(14).mean()
        rsi = (100 - (100/(1 + (up/down)))).iloc[-1]
        
        return {
            'is_valid': is_breakout and is_vol_pump,
            'lp': int(lp),
            'rsi': int(rsi),
            'vol_ratio': round(df['Volume'].iloc[-1] / avg_vol, 1),
            'prev_high': int(prev_high)
        }
    except: return None

# --- UI HEADER ---
st.markdown("""
<div class='status-card bg-breakout'>
    <h1 style='margin:0; color:#c7d2fe;'>🏹 GOD MODE V41.1: BREAKOUT HUNTER</h1>
    <p style='margin:5px 0 0 0; opacity:0.9;'>Mendeteksi Awal Ledakan Harga | Toleransi Delay 15 Menit | Anti-Zombie Filter</p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🏹 Hunting Control")
    min_vol_ratio = st.slider("Minimal Lonjakan Volume (x Lipat)", 1.2, 5.0, 1.5)
    strict_fundamental = st.toggle("🔒 Wajib Laba (EPS > 0)", value=True)
    st.divider()
    capital = st.number_input("Modal Trading (Rp)", value=1000000)
    risk_pct = st.slider("Toleransi Rugi (%)", 1.0, 5.0, 3.0)

# --- EXECUTION ---
if st.button("🚀 MULAI BERBURU MOMENTUM", use_container_width=True, type="primary"):
    with st.status("Memindai 50 Saham Teraktif...", expanded=True) as status:
        try:
            q = (Query().set_markets('indonesia')
                 .select('name','close','volume','sector')
                 .where(Column('market_cap_basic') >= 1e11))
            _, df_raw = q.get_scanner_data()
            
            valid_found = 0
            for idx, row in df_raw.head(50).iterrows():
                t_sym = row['name']
                
                # 1. Filter Fundamental
                is_ok, eps = check_fundamentals(t_sym)
                if strict_fundamental and not is_ok: continue
                
                # 2. Deteksi Breakout
                data = detect_breakout(t_sym)
                if data and data['is_valid'] and data['vol_ratio'] >= min_vol_ratio:
                    valid_found += 1
                    
                    # Kalkulasi Rencana Trading
                    entry = data['lp']
                    sl_price = entry * (1 - (risk_pct/100))
                    tp_price = entry * (1 + (risk_pct * 3 / 100)) # Target 1:3
                    lot = int((capital / entry) / 100)
                    
                    st.markdown(f"""
                    <div class='stock-card'>
                        <h2 style='margin:0; color:#818cf8;'>{t_sym} <span style='font-size:12px; color:#94a3b8;'>({row['sector']})</span></h2>
                        <div style='margin-top:10px;'>
                            <span class='indicator-tag' style='background:#1e3a8a; color:#60a5fa;'>🚀 Breakout High 20D</span>
                            <span class='indicator-tag' style='background:#064e3b; color:#34d399;'>📊 Vol x{data['vol_ratio']}</span>
                            <span class='indicator-tag' style='background:#312e81; color:#a5b4fc;'>🏛️ EPS: Rp {eps}</span>
                        </div>
                        <p style='margin:10px 0; font-size:15px;'>Harga Sekarang: <b>Rp {entry}</b> (Menembus High Rp {data['prev_high']})</p>
                        <div style='background-color:#1e293b; padding:15px; border-radius:8px; border:1px solid #334155;'>
                            <b>🎯 INSTRUKSI EKSEKUSI:</b><br>
                            - Cek harga LIVE di sekuritas Anda.<br>
                            - Jika masih di sekitar <b>Rp {entry}</b>, segera entry <b>{lot} Lot</b>.<br>
                            - Pasang Jual Otomatis (Take Profit) di: <b>Rp {int(tp_price)}</b>.<br>
                            - Pasang Batas Rugi (Stop Loss) di: <b>Rp {int(sl_price)}</b>.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            status.update(label="Berburu Selesai!", state="complete")
            if valid_found == 0:
                st.warning("Belum ada ledakan volume yang valid hari ini. Pasar sedang tenang.")
        except Exception as e:
            st.error(f"Error: {e}")