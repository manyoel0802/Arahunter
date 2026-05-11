import streamlit as st
import pandas as pd
import yfinance as yf
import warnings
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
        # Menarik seluruh data saham Indonesia dengan Market Cap > 100 Miliar
        q = (Query().set_markets('indonesia')
             .select('name','close','sector','Perf.1M','market_cap_basic')
             .where(Column('market_cap_basic') >= 1e11))
        _, df = q.get_scanner_data()
        return df.dropna(subset=['sector'])
    except: return pd.DataFrame()

def check_trend(ticker):
    try:
        # Menarik data 6 bulan terakhir untuk mencari SMA 50
        df = yf.Ticker(f"{ticker}.JK").history(period="6mo")
        if df.empty or len(df) < 50: return "UNKNOWN"
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        # Logika Bullish/Bearish
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

# Menarik data awal untuk mendapatkan daftar sektor
df_raw = get_market_data()

if not df_raw.empty:
    # Mengambil daftar sektor unik langsung dari TradingView
    sektor_list = sorted(df_raw['sector'].unique().tolist())
    
    # --- 🎛️ SIDEBAR ---
    with st.sidebar:
        st.header("🎛️ Pengaturan Radar")
        # Kolom untuk memilih sektor (Otomatis terisi daftar sektor BEI)
        selected_sector = st.selectbox("🔍 Pilih Sektor Target:", ["-- Pilih Sektor --"] + sektor_list)
        st.divider()
        st.info("Aplikasi akan memindai status trend:\n\n🟢 **BULLISH:** Harga > SMA 50\n🔴 **BEARISH:** Harga < SMA 50")

    # --- 🚀 EXECUTION ENGINE ---
    if selected_sector != "-- Pilih Sektor --":
        # Filter hanya saham di sektor yang dipilih
        df_sector = df_raw[df_raw['sector'] == selected_sector]
        
        st.subheader(f"📊 Memantau Sektor: {selected_sector} ({len(df_sector)} Saham)")
        
        if st.button(f"🚀 Mulai Pemindaian Sektor", type="primary"):
            with st.spinner(f"Menarik data teknikal untuk sektor {selected_sector}..."):
                
                # Membagi tampilan menjadi 3 kolom agar lebih rapi
                col1, col2, col3 = st.columns(3)
                bullish_count = 0
                bearish_count = 0
                
                # Looping pengecekan setiap saham di sektor tersebut
                for idx, row in df_sector.iterrows():
                    t_sym = row['name']
                    trend = check_trend(t_sym)
                    
                    if trend == "BULLISH":
                        bullish_count += 1
                        badge = "<span class='bullish-badge'>🟢 BULLISH</span>"
                        border_color = "#10b981" # Hijau
                    elif trend == "BEARISH":
                        bearish_count += 1
                        badge = "<span class='bearish-badge'>🔴 BEARISH</span>"
                        border_color = "#ef4444" # Merah
                    else:
                        badge = "⚪ UNKNOWN"
                        border_color = "#6b7280"
                        
                    card_html = f"""
                    <div class='stock-card' style='border-left: 5px solid {border_color};'>
                        <h3 style='margin-bottom: 5px;'>{t_sym} {badge}</h3>
                        <p style='margin: 0; font-size: 14px; color: #9ca3af;'>Harga: Rp {row['close']} | Perf 1B: {row['Perf.1M']:.2f}%</p>
                    </div>
                    """
                    
                    # Mendistribusikan kartu ke dalam 3 kolom
                    col_index = idx % 3
                    if col_index == 0:
                        with col1: st.markdown(card_html, unsafe_allow_html=True)
                    elif col_index == 1:
                        with col2: st.markdown(card_html, unsafe_allow_html=True)
                    else:
                        with col3: st.markdown(card_html, unsafe_allow_html=True)
                        
            # Menampilkan kesimpulan kekuatan sektor
            st.divider()
            st.success(f"**Kesimpulan Sektor {selected_sector}:** Ditemukan {bullish_count} Saham Bullish dan {bearish_count} Saham Bearish.")
else:
    st.error("Gagal terhubung ke radar utama. Silakan muat ulang halaman.")