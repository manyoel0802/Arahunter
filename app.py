import streamlit as st
import pandas as pd
from tradingview_screener import Query, Column

st.set_page_config(page_title="Super Kilat ARA Hunter", layout="wide")

st.title("⚡ Super Kilat ARA Hunter (Powered by TradingView)")
st.caption("Memindai 900+ saham IHSG dalam 1 Detik tanpa takut diblokir (Anti Rate-Limit)")

# --- FILTER PENGGUNA ---
col1, col2 = st.columns(2)
with col1:
    min_naik = st.number_input("Minimal Naik (%)", value=2.0)
with col2:
    min_vol = st.number_input("Minimal Volume Hari Ini (Lembar)", value=1000000) # 1 Juta Lembar = 10 Ribu Lot

if st.button("🚀 SCAN SELURUH PASAR (1 Detik)", type="primary"):
    with st.spinner("Menarik data 900+ saham dari TradingView..."):
        try:
            # RAHASIA KECEPATAN: Kita minta server TradingView yang menyeleksi, bukan komputer kita!
            query = (Query()
                     .set_markets('indonesia') # Hanya IHSG
                     .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'RSI', 'SMA50', 'MACD.macd', 'MACD.signal')
                     .where(
                         Column('change') >= min_naik,          # Filter Kenaikan
                         Column('volume') >= min_vol,           # Filter Likuiditas
                         Column('close') > Column('SMA50'),     # Filter Uptrend (Harga di atas MA50)
                         Column('RSI') > 50                     # Filter Momentum Positif
                     ))
            
            # Eksekusi Query (Hanya butuh 1-2 detik!)
            _, df = query.get_scanner_data()
            
            if not df.empty:
                # Membersihkan tabel agar enak dibaca
                df = df.rename(columns={
                    'name': 'Saham',
                    'close': 'Harga',
                    'change': 'Naik (%)',
                    'volume': 'Vol Hari Ini',
                    'average_volume_10d_calc': 'Rata-rata Vol 10H',
                    'SMA50': 'MA50',
                    'MACD.macd': 'MACD',
                    'MACD.signal': 'Signal'
                })
                
                # Membulatkan angka desimal
                df['Naik (%)'] = df['Naik (%)'].round(2)
                df['RSI'] = df['RSI'].round(2)
                df['Harga'] = df['Harga'].astype(int)
                
                # Menambahkan rasio lonjakan volume
                df['Vol Ratio (x)'] = (df['Vol Hari Ini'] / df['Rata-rata Vol 10H']).round(1)
                
                # Mengurutkan dari kenaikan tertinggi
                df = df.sort_values('Naik (%)', ascending=False).reset_index(drop=True)
                
                # Membuang kolom yang tidak perlu ditampilkan
                df_tampil = df[['Saham', 'Harga', 'Naik (%)', 'Vol Ratio (x)', 'RSI', 'MA50', 'MACD']]
                
                st.success(f"🔥 BINGO! Ditemukan {len(df)} Saham Uptrend dalam hitungan detik!")
                st.dataframe(df_tampil, use_container_width=True)
            else:
                st.warning("Tidak ada saham yang memenuhi kriteria saat ini.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan koneksi: {e}")