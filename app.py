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
    .score-high { color: #fbbf24; font-weight: bold; font-size: 15px; } /* Emas untuk > 80% */
    .score-med { color: #e5e7eb; font-weight: bold; font-size: 15px; }  /* Putih untuk > 50% */
    .score-low { color: #6b7280; font-weight: bold; font-size: 15px; }  /* Abu-abu untuk < 50% */
    </style>
    """, unsafe_allow_html=True)

# --- 🌍 CORE ENGINES ---
@st.cache_data(ttl=1800)
def get_market_data():
    try:
        q = (Query().set_markets('indonesia')
             .select('name','close','sector','Perf.1M','market_cap_basic')
             .where(Column('market_cap_basic') >= 1e11)
             .limit(1000)) 
        _, df = q.get_scanner_data()
        return df.dropna(subset=['sector'])
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_ihsg_data():
    try:
        return yf.Ticker("^JKSE").history(period="1y")
    except: return pd.DataFrame()

def get_ultimate_bull_probability(df_stock, df_ihsg):
    try:
        # Jika data kurang dari 200 hari, skor tidak bisa dihitung maksimal
        if len(df_stock) < 200 or df_ihsg.empty: return 0 
        
        score = 0
        c = df_stock['Close'].iloc[-1]
        
        # 1. TREN MAKRO
        sma50 = df_stock['Close'].rolling(50).mean().iloc[-1]
        sma150 = df_stock['Close'].rolling(150).mean().iloc[-1]
        sma200 = df_stock['Close'].rolling(200).mean().iloc[-1]
        
        if c > sma50: score += 5
        if c > sma150: score += 5
        if c > sma200: score += 5
        if sma50 > sma150 and sma150 > sma200: score += 10 
        
        # 2. RELATIVE STRENGTH (vs IHSG)
        stock_perf_3m = (c - df_stock['Close'].iloc[-60]) / df_stock['Close'].iloc[-60]
        ihsg_perf_3m = (df_ihsg['Close'].iloc[-1] - df_ihsg['Close'].iloc[-60]) / df_ihsg['Close'].iloc[-60]
        
        if stock_perf_3m > 0: score += 5
        if stock_perf_3m > ihsg_perf_3m: score += 10
        if stock_perf_3m > (ihsg_perf_3m * 2): score += 10
        
        # 3. VOLUME & BANDAR FOOTPRINT
        range_hl = (df_stock['High'] - df_stock['Low']).replace(0, 1e-10) 
        mf_multiplier = ((df_stock['Close'] - df_stock['Low']) - (df_stock['High'] - df_stock['Close'])) / range_hl
        mf_volume = mf_multiplier * df_stock['Volume']
        cmf = (mf_volume.rolling(20).sum() / df_stock['Volume'].rolling(20).sum()).iloc[-1]
        
        vol_sma50 = df_stock['Volume'].rolling(50).mean().iloc[-1]
        vol_today = df_stock['Volume'].iloc[-1]
        
        if cmf > 0.05: score += 10
        if cmf > 0.15: score += 5
        if vol_today > (vol_sma50 * 1.5): score += 10
        
        # 4. MOMENTUM 52-WEEK HIGH
        high_52w = df_stock['High'].tail(250).max()
        low_52w = df_stock['Low'].tail(250).min()
        distance_to_high = (high_52w - c) / high_52w
        
        if c > (low_52w * 1.3): score += 5
        if distance_to_high <= 0.25: score += 10
        if distance_to_high <= 0.10: score += 10
        
        return int(min(score, 100))
    except: return 0

# --- UI HEADER ---
st.markdown(f"""
<div class='status-card bg-sector'>
    <h1 style='margin:0; color:#ddd6fe;'>🧭 SECTOR TREND RADAR</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#a78bfa;'>
        Pemantau Kekuatan Trend & The 90% Confluence Score
    </p>
</div>
""", unsafe_allow_html=True)

df_raw = get_market_data()
df_ihsg = get_ihsg_data()

if not df_raw.empty:
    sektor_list = sorted(df_raw['sector'].unique().tolist())
    
    # --- 🎛️ SIDEBAR ---
    with st.sidebar:
        st.header("🎛️ Pengaturan Radar")
        selected_sector = st.selectbox("🔍 Pilih Sektor Target:", ["-- Pilih Sektor --"] + sektor_list)
        st.divider()
        st.info("Aplikasi akan memindai status trend:\n\n🟢 **BULLISH:** Harga > SMA 50\n🔴 **BEARISH:** Harga < SMA 50\n\n🎯 **SKOR PROBABILITAS** menilai Konfluensi Fundamental, Teknikal & Bandar (Maks 100%).")

    # --- 🚀 EXECUTION ENGINE ---
    if selected_sector != "-- Pilih Sektor --":
        
        df_sector = df_raw[df_raw['sector'] == selected_sector].sort_values(by='Perf.1M', ascending=False).reset_index(drop=True)
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
                
                # Tarik data 1 Tahun untuk kalkulasi 52-Week High
                df_hist = pd.DataFrame()
                try: df_hist = yf.Ticker(f"{t_sym}.JK").history(period="1y")
                except: pass
                
                time.sleep(0.1) # Delay anti-banned
                
                trend = "UNKNOWN"
                score = 0
                
                if not df_hist.empty and len(df_hist) >= 50:
                    sma50 = df_hist['Close'].rolling(50).mean().iloc[-1]
                    trend = "BULLISH" if df_hist['Close'].iloc[-1] > sma50 else "BEARISH"
                    score = get_ultimate_bull_probability(df_hist, df_ihsg)
                
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
                
                # Penyesuaian warna teks skor
                if score >= 80: score_class = "score-high"
                elif score >= 50: score_class = "score-med"
                else: score_class = "score-low"
                
                # Menambahkan emoji khusus untuk saham super
                unicorn = " 🦄" if score >= 90 else ""
                    
                card_html = f"""
                <div class='stock-card' style='border-left: 5px solid {border_color};'>
                    <h3 style='margin-bottom: 5px;'>{t_sym} {badge}</h3>
                    <p style='margin: 5px 0; font-size: 14px; color: #9ca3af;'>Harga: Rp {row['close']} | Perf 1B: {row['Perf.1M']:.2f}%</p>
                    <p style='margin: 0;'><span class='{score_class}'>🎯 Skor Probabilitas: {score}%{unicorn}</span></p>
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