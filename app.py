import streamlit as st
import pandas as pd
import yfinance as yf
import warnings
import time
from tradingview_screener import Query, Column

# --- CONFIG & SECURITY ---
warnings.filterwarnings('ignore')
st.set_page_config(page_title="SECTOR RADAR", layout="wide", page_icon="🧭")

# --- TEMA VISUAL UNGU KLASIK (PRESERVED) ---
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

# --- 🌍 CORE ENGINES ---
@st.cache_data(ttl=1800)
def get_market_data():
    try:
        q = (Query().set_markets('indonesia')
             .select('name','close','sector','Perf.1M','market_cap_basic')
             .where(Column('market_cap_basic') >= 1e11))
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
        
        # FIX 1: Reset Index agar pembagian kolom tidak bentrok
        df_sector = df_raw[df_raw['sector'] == selected_sector].reset_index(drop=True)
        total_saham = len(df_sector)
        
        st.subheader(f"📊 Memantau Sektor: {selected_sector} ({total_saham} Saham)")
        
        if st.button(f"🚀 Mulai Pemindaian Sektor", type="primary"):
            
            # Menambahkan indikator visual Progress Bar
            progress_bar = st.progress(0, text="Menghidupkan mesin radar...")
            
            col1, col2, col3 = st.columns(3)
            bullish_count = 0
            bearish_count = 0
            
            for idx, row in df_sector.iterrows():
                t_sym = row['name']
                
                # Update text progress bar
                progress_bar.progress((idx + 1) / total_saham, text=f"Memindai: {t_sym} ({idx + 1}/{total_saham} saham)")
                
                trend = check_trend(t_sym)
                time.sleep(0.1) # FIX 2: Delay agar server Yahoo tidak memblokir aplikasi
                
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
                
                # Pembagian merata ke 3 kolom berdasarkan index yang sudah di-reset
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