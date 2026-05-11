import streamlit as st
import pandas as pd
import yfinance as yf
import warnings
import time
from tradingview_screener import Query, Column

# --- CONFIG & SECURITY ---
warnings.filterwarnings('ignore')
st.set_page_config(page_title="SECTOR RADAR", layout="wide", page_icon="🧭")

# --- TEMA VISUAL UNGU KLASIK ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-sector { background: linear-gradient(135deg, #2e1065 0%, #4c1d95 50%, #3b0764 100%); border-top: 5px solid #8b5cf6; box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .bullish-badge { background-color: #059669; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 10px; }
    .bearish-badge { background-color: #dc2626; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 🌍 CORE ENGINES (LIMITER DIBUKA) ---
@st.cache_data(ttl=1800)
def get_market_data():
    try:
        # 💉 SUNTIKAN: .limit(1000) dipasang untuk menarik seluruh saham, bukan cuma 50
        q = (Query().set_markets('indonesia')
             .select('name','close','sector','Perf.1M','market_cap_basic')
             .where(Column('market_cap_basic') >= 1e11)
             .limit(1000)) 
        _, df = q.get_scanner_data()
        return df.dropna(subset=['sector'])
    except: return pd.DataFrame()

def check_trend(ticker):
    try:
        df = yf.Ticker(f"{ticker}.JK").history(period="6mo")
        if df.empty or len(df) < 50: return "UNKNOWN"
        df['SMA50'] = df['Close'].rolling(50).mean()
        if df['Close'].iloc[-1] > df['SMA50'].iloc[-1]:
            return "BULLISH"
        else:
            return "BEARISH"
    except: return "UNKNOWN"

# --- UI HEADER ---
st.markdown(f"""
<div class='status-card bg-sector'>
    <h1 style='margin:0; color:#ddd6fe;'>🧭 SECTOR TREND RADAR</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#a78bfa;'>
        Pemantau Kekuatan Trend (Bullish/Bearish) Terfokus Per Sektor
    </p>
</div>
""", unsafe_allow_html=True)

df_raw = get_market_data()

if not df_raw.empty:
    sektor_list = sorted(df_raw['sector'].unique().tolist())
    
    # --- 🎛️ SIDEBAR ---
    with st.sidebar:
        st.header("🎛️ Pengaturan Radar")
        selected_sector = st.selectbox("🔍 Pilih Sektor Target:", ["-- Pilih Sektor --"] + sektor_list)
        st.divider()
        st.info("Aplikasi akan memindai status trend:\n\n🟢 **BULLISH:** Harga > SMA 50\n🔴 **BEARISH:** Harga < SMA 50")

    # --- 🚀 EXECUTION ENGINE ---
    if selected_sector != "-- Pilih Sektor --":
        
        df_sector = df_raw[df_raw['sector'] == selected_sector].reset_index(drop=True)
        total_saham = len(df_sector)
        
        st.subheader(f"📊 Memantau Sektor: {selected_sector} ({total_saham} Saham)")
        
        if st.button(f"🚀 Mulai Pemindaian Sektor", type="primary"):
            
            progress_bar = st.progress(0, text="Menghidupkan mesin radar...")
            
            col1, col2, col3 = st.columns(3)
            bullish_count = 0
            bearish_count = 0
            
            for idx, row in df_sector.iterrows():
                t_sym = row['name']
                
                progress_bar.progress((idx + 1) / total_saham, text=f"Memindai: {t_sym} ({idx + 1}/{total_saham} saham)")
                
                trend = check_trend(t_sym)
                time.sleep(0.1) 
                
                if trend == "BULLISH":
                    bullish_count += 1
                    badge = "<span class='bullish-badge'>🟢 BULLISH</span>"
                    border_color = "#10b981"
                elif trend == "BEARISH":
                    bearish_count += 1
                    badge = "<span class='bearish-badge'>🔴 BEARISH</span>"
                    border_color = "#ef4444"
                else:
                    badge = "⚪ UNKNOWN"
                    border_color = "#6b7280"
                    
                card_html = f"""
                <div class='stock-card' style='border-left: 5px solid {border_color};'>
                    <h3 style='margin-bottom: 5px;'>{t_sym} {badge}</h3>
                    <p style='margin: 0; font-size: 14px; color: #9ca3af;'>Harga: Rp {row['close']} | Perf 1B: {row['Perf.1M']:.2f}%</p>
                </div>
                """
                
                if idx % 3 == 0:
                    with col1: st.markdown(card_html, unsafe_allow_html=True)
                elif idx % 3 == 1:
                    with col2: st.markdown(card_html, unsafe_allow_html=True)
                else:
                    with col3: st.markdown(card_html, unsafe_allow_html=True)
                    
            progress_bar.progress(1.0, text="✅ Pemindaian Selesai!")
            st.divider()
            st.success(f"**Kesimpulan Sektor {selected_sector}:** Ditemukan {bullish_count} Saham Bullish dan {bearish_count} Saham Bearish.")
else:
    st.error("Gagal terhubung ke radar utama. Silakan muat ulang halaman.")

def get_ultimate_bull_probability(df_stock, df_ihsg):
    """
    Algoritma Penilaian Konfluensi Total (Maksimal 100 Poin / 100%)
    """
    try:
        score = 0
        
        # 1. PILAR TREN MAKRO (Maks 25 Poin)
        c = df_stock['Close'].iloc[-1]
        sma50 = df_stock['Close'].rolling(50).mean().iloc[-1]
        sma150 = df_stock['Close'].rolling(150).mean().iloc[-1]
        sma200 = df_stock['Close'].rolling(200).mean().iloc[-1]
        
        if c > sma50: score += 5
        if c > sma150: score += 5
        if c > sma200: score += 5
        if sma50 > sma150 > sma200: score += 10 # Golden alignment
        
        # 2. PILAR RELATIVE STRENGTH vs IHSG (Maks 25 Poin)
        # Menghitung performa 3 bulan terakhir (sekitar 60 hari bursa)
        stock_perf_3m = (c - df_stock['Close'].iloc[-60]) / df_stock['Close'].iloc[-60]
        ihsg_perf_3m = (df_ihsg['Close'].iloc[-1] - df_ihsg['Close'].iloc[-60]) / df_ihsg['Close'].iloc[-60]
        
        if stock_perf_3m > 0: score += 5
        if stock_perf_3m > ihsg_perf_3m: score += 10 # Outperforming pasar
        if stock_perf_3m > (ihsg_perf_3m * 2): score += 10 # Memimpin pasar secara absolut
        
        # 3. PILAR ANOMALI VOLUME & BANDAR (Maks 25 Poin)
        # Chaikin Money Flow (CMF) 20 hari
        range_hl = (df_stock['High'] - df_stock['Low']).replace(0, 1e-10) 
        mf_multiplier = ((df_stock['Close'] - df_stock['Low']) - (df_stock['High'] - df_stock['Close'])) / range_hl
        mf_volume = mf_multiplier * df_stock['Volume']
        cmf = (mf_volume.rolling(20).sum() / df_stock['Volume'].rolling(20).sum()).iloc[-1]
        
        vol_sma50 = df_stock['Volume'].rolling(50).mean().iloc[-1]
        vol_today = df_stock['Volume'].iloc[-1]
        
        if cmf > 0.05: score += 10 # Akumulasi stabil
        if cmf > 0.15: score += 5  # Akumulasi agresif
        if vol_today > (vol_sma50 * 1.5): score += 10 # Ledakan volume validasi
        
        # 4. PILAR MOMENTUM 52-WEEK HIGH (Maks 25 Poin)
        # Mengambil harga tertinggi dalam 250 hari bursa (1 tahun)
        high_52w = df_stock['High'].tail(250).max()
        low_52w = df_stock['Low'].tail(250).min()
        
        # Seberapa dekat harga saat ini dengan puncak 52 minggunya? (Persentase)
        distance_to_high = (high_52w - c) / high_52w
        
        if c > (low_52w * 1.3): score += 5 # Sudah naik minimal 30% dari dasar jurang
        if distance_to_high <= 0.25: score += 10 # Berada dalam jarak 25% dari titik tertinggi
        if distance_to_high <= 0.10: score += 10 # Berada di pucuk momentum (siap breakout)
        
        return score # Hasilnya adalah persentase (0 - 100)
        
    except Exception as e:
        return 0 # Jika data tidak lengkap, gagalkan secara otomatis