import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

st.set_page_config(page_title="CRYPTO ORACLE V50.0", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .main { background-color: #09090b; }
    .stMetric { background-color: #18181b; border: 1px solid #27272a; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #3f3f46; color: white; }
    .bg-crypto { background: linear-gradient(135deg, #0f172a 0%, #0284c7 50%, #082f49 100%); border-top: 5px solid #38bdf8; box-shadow: 0 4px 20px rgba(56, 189, 248, 0.3); }
    .crypto-card { background-color: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #f59e0b; }
    </style>
    """, unsafe_allow_html=True)

# --- ⚡ CRYPTO ENGINES ---
@st.cache_data(ttl=300) # Cache 5 menit karena crypto bergerak 24/7
def get_btc_macro():
    try:
        btc = yf.Ticker("BTC-USD").history(period="1mo")
        btc_return = ((btc['Close'].iloc[-1] / btc['Close'].iloc[0]) - 1) * 100
        return btc_return
    except: return 0.0

btc_return_1mo = get_btc_macro()

def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def detect_crypto_squeeze(df):
    try:
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Band_Width'] = ((df['SMA20'] + (df['STD20'] * 2)) - (df['SMA20'] - (df['STD20'] * 2))) / df['SMA20']
        return df['Band_Width'].iloc[-1] <= (df['Band_Width'].tail(20).min() * 1.2) # Toleransi wicks crypto
    except: return False

def check_crypto_trend(df):
    try:
        # Crypto bergerak lebih cepat, kita gunakan SMA 20 dan SMA 50 sebagai penentu tren utama
        c, sma20, sma50 = df['Close'].iloc[-1], df['Close'].rolling(20).mean().iloc[-1], df['Close'].rolling(50).mean().iloc[-1]
        return (c > sma20 and c > sma50 and sma20 > sma50)
    except: return False

# --- UI HEADER ---
st.markdown("""
<div class='status-card bg-crypto'>
    <h1 style='margin:0; color:#f0f9ff;'>⚡ GOD MODE V50.0: CRYPTO ORACLE</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#bae6fd;'>
        24/7 Market Radar | Altcoin Relative Strength (vs BTC) | Volatility Squeeze Engine
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Tactical Command")
    capital_usd = st.number_input("Modal Trading (USD)", value=1000, step=100)
    risk_pct = st.slider("Max Loss Per Trade (%)", 1.0, 5.0, 2.0, step=0.5)
    
    st.divider()
    st.header("🛡️ Crypto Filters")
    strict_rs = st.toggle("👑 Wajib Kalahkan Bitcoin", value=True, help="Hanya cari Altcoin yang kenaikannya lebih tinggi dari BTC bulan ini.")

# --- EXECUTION ENGINE ---
if st.button("🚀 SCAN TOP CRYPTO ASSETS", use_container_width=True, type="primary"):
    with st.status("Memindai Aliran Uang Global...", expanded=True) as status:
        try:
            # Daftar Top Koin Global (Bisa ditambah)
            crypto_list = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'DOGE-USD', 'ADA-USD', 'AVAX-USD', 'LINK-USD', 'DOT-USD', 'NEAR-USD', 'RENDER-USD']
            
            valid_coins = 0
            st.write(f"Performa Bitcoin (BTC) 1 Bulan Terakhir: **{btc_return_1mo:.2f}%**")
            
            for t_sym in crypto_list:
                df_hist = yf.Ticker(t_sym).history(period="6mo")
                
                if not df_hist.empty and check_crypto_trend(df_hist):
                    # Cek Likuiditas (Volume Dolar Harian harus besar > $50 Juta)
                    avg_vol_usd = (df_hist['Volume'].tail(5).mean() * df_hist['Close'].tail(5).mean())
                    if avg_vol_usd < 50_000_000: continue
                    
                    # Cek Relative Strength vs BTC
                    coin_ret_1mo = ((df_hist['Close'].iloc[-1] / df_hist['Close'].iloc[-21]) - 1) * 100
                    if strict_rs and t_sym != 'BTC-USD' and coin_ret_1mo <= btc_return_1mo: continue
                    
                    # Cek Setup Ledakan (Squeeze)
                    if detect_crypto_squeeze(df_hist):
                        atr = calculate_atr(df_hist)
                        lp = float(df_hist['Close'].iloc[-1])
                        sma20 = float(df_hist['Close'].rolling(20).mean().iloc[-1])
                        
                        # Trigger Price Kripto
                        trigger_price = max(sma20, lp)
                        
                        # Stop Loss Kripto butuh ruang nafas lebih lebar (ATR x 2.5) karena ekor lilin (wicks) panjang
                        sl_price = trigger_price - (atr * 2.5) 
                        target_price = trigger_price + (atr * 5.0) 
                        
                        risk_usd = trigger_price - sl_price
                        rrr = round((target_price - trigger_price) / risk_usd, 1) if risk_usd > 0 else 0
                        
                        if rrr < 2.0: continue 
                        
                        sl_pct = round(((trigger_price - sl_price) / trigger_price) * 100, 1)
                        max_loss_usd = capital_usd * (risk_pct/100)
                        
                        # Hitung Ukuran Koin (Bukan Lot)
                        coin_size = max_loss_usd / risk_usd if risk_usd > 0 else 0
                        
                        valid_coins += 1
                        
                        html_card = f"<div class='crypto-card'><h2 style='margin:0; color:#f59e0b;'>{t_sym.replace('-USD', '')} <span style='font-size:14px; background:#451a03; color:#fcd34d; padding:2px 8px; border-radius:4px;'>USDT PAIR</span></h2><p style='color:#a1a1aa; font-size:14px; margin:0 0 10px 0;'>Daily Vol: <b>${(avg_vol_usd/1_000_000):.1f}M</b> | 1Mo Return: <b>+{coin_ret_1mo:.1f}%</b></p><div style='background-color:#09090b; padding:15px; border-radius:8px; border:1px solid #27272a;'><ul style='margin:0; padding-left:20px; font-size:14px; color:#10b981; line-height:1.6;'><li><b>Alpha Asset:</b> Mengalahkan performa Bitcoin.</li><li><b>Momentum:</b> Volatilitas sangat sempit (Squeeze), bersiap untuk ledakan arah tren.</li></ul></div></div>"
                        st.markdown(html_card, unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("🎯 ENTRY (Limit Order)", f"${trigger_price:.4f}")
                        c2.metric("🛡️ STOP LOSS", f"${sl_price:.4f}", f"-{sl_pct}%")
                        c3.metric("📦 POSITION SIZE", f"{coin_size:.4f} KOIN")

            status.update(label=f"Scan Kripto Selesai!", state="complete", expanded=False)
            if valid_coins == 0: st.warning("Mesin tidak menemukan Altcoin yang mengalahkan BTC dengan setup Squeeze. Pasar mungkin sedang konsolidasi atau koreksi.")
        except Exception as e:
            st.error(f"Engine Error: {e}")