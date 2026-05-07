import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests

st.set_page_config(page_title="GOD MODE V42.0", layout="wide", page_icon="🛡️")

# --- 🛡️ PRO-TERMINAL ENGINES ---
def check_pro_filters(ticker):
    try:
        # Ambil data harian 1 bulan
        df = yf.Ticker(f"{ticker}.JK").history(period="1mo")
        if len(df) < 20: return None
        
        lp = df['Close'].iloc[-1]
        avg_vol = df['Volume'].iloc[-21:-1].mean()
        current_vol = df['Volume'].iloc[-1]
        
        # 1. LIQUIDITY FILTER (Min Rp 5 Miliar Turnover)
        turnover = lp * current_vol
        is_liquid = turnover >= 5_000_000_000
        
        # 2. VOLUME SPIKE (Min 3x Average)
        vol_ratio = current_vol / avg_vol
        is_vol_valid = vol_ratio >= 3.0
        
        # 3. PRICE BREAKOUT
        prev_high = df['High'].iloc[-21:-1].max()
        is_breakout = lp > prev_high
        
        return {
            'valid': is_liquid and is_vol_valid and is_breakout,
            'turnover': turnover / 1e9, # Dalam Miliar
            'vol_ratio': vol_ratio,
            'lp': int(lp)
        }
    except: return None

# --- UI HEADER ---
st.markdown("""
<div style='background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding:25px; border-radius:15px; border-left: 8px solid #10b981; color:white;'>
    <h1 style='margin:0;'>🛡️ GOD MODE V42.0: THE PRO-TERMINAL</h1>
    <p style='margin:5px 0 0 0; opacity:0.8;'>Liquidity Secured (>5B) | Volume Spike 3x | Breakout Engine</p>
</div>
""", unsafe_allow_html=True)

# --- EXECUTION ---
if st.button("🚀 SCAN FOR INSTITUTIONAL SETUPS", use_container_width=True, type="primary"):
    with st.status("Memfilter Saham 'Zombie' dan 'Sepi'...", expanded=True) as status:
        # Gunakan list saham teraktif atau top market cap untuk efisiensi
        candidates = ["PANI", "AMMN", "BBRI", "BRPT", "BREN", "TPIA", "GOTO", "TLKM", "ASII", "ADRO", "ITMG", "PTBA"] 
        found = 0
        
        for t in candidates:
            res = check_pro_filters(t)
            if res and res['valid']:
                found += 1
                st.success(f"🎯 TARGET DITEMUKAN: {t}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Harga", res['lp'])
                c2.metric("Turnover", f"{res['turnover']:.1f} Miliar")
                c3.metric("Vol Spike", f"{res['vol_ratio']:.1f}x")
                
        status.update(label="Scanning Selesai!", state="complete")
        if found == 0:
            st.warning("Pasar sedang sepi. Tidak ada saham likuid yang breakout hari ini. Modal Anda aman di kantong.")