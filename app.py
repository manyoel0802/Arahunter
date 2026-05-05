import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime
from tradingview_screener import Query, Column

warnings = pd.options.mode.chained_assignment = None

st.set_page_config(page_title="Ultimate ARA Hunter", layout="centered", page_icon="👑")

st.title("👑 Ultimate ARA Hunter (V8.0)")
st.caption("TradingView Super-Engine | Techno-Fundamental | Auto-Scan | Anti-Trap")

# --- UI PENGATURAN FILTER ---
with st.expander("⚙️ Buka Pengaturan Filter Lanjutan", expanded=True):
    st.subheader("1. Filter Kategori & Fundamental")
    pakai_fundo = st.checkbox("Aktifkan Filter Valuasi (PBV & ROE)", value=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        opsi_mc = st.selectbox("Market Cap", ["Semua Ukuran", "Mulai Rp 500 M", "Mulai Rp 1 T", "Mulai Rp 10 T"])
    with col2:
        max_pbv = st.number_input("Max PBV (x)", value=2.0, step=0.5) if pakai_fundo else 999
    with col3:
        min_roe = st.number_input("Min ROE (%)", value=15.0, step=1.0) if pakai_fundo else -999

    st.subheader("2. Filter Teknikal & Momentum")
    col4, col5 = st.columns(2)
    with col4:
        min_kenaikan = st.number_input("Minimal Naik (%)", value=2.0, step=0.5)
    with col5:
        min_vol_ratio = st.number_input("Min Vol Loncat (x Rata-rata)", value=1.5, step=0.5)

# Konversi Text Market Cap ke Angka
if "Semua Ukuran" in opsi_mc: min_mc_angka = 0
elif "500 M" in opsi_mc: min_mc_angka = 500_000_000_000
elif "1 T" in opsi_mc: min_mc_angka = 1_000_000_000_000
else: min_mc_angka = 10_000_000_000_000

st.divider()

# --- FITUR AUTO SCAN ---
col_btn, col_auto = st.columns([1, 1])
with col_btn:
    tombol_manual = st.button("🚀 SCAN SELURUH PASAR SEKARANG", use_container_width=True, type="primary")
with col_auto:
    mode_auto = st.toggle("🔄 Auto-Scan (15 Menit)")

# --- FUNGSI MENGGAMBAR GRAFIK (YFINANCE) ---
def gambar_grafik(ticker_bersih):
    try:
        # Tambahkan .JK hanya untuk Yfinance menggambar chart
        saham = yf.Ticker(f"{ticker_bersih}.JK")
        df_chart = saham.history(period="3mo")
        df_chart['MA50'] = df_chart['Close'].rolling(window=50).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_chart.index[-40:], open=df_chart['Open'][-40:], 
            high=df_chart['High'][-40:], low=df_chart['Low'][-40:], 
            close=df_chart['Close'][-40:], name="Harga"
        ))
        fig.add_trace(go.Scatter(
            x=df_chart.index[-40:], y=df_chart['MA50'][-40:], 
            line=dict(color='yellow', width=2), name='MA50 (Uptrend)'
        ))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.caption("Grafik gagal dimuat untuk saham ini.")

# --- LOGIKA EKSEKUSI TRADINGVIEW ---
if tombol_manual or mode_auto:
    waktu_sekarang = datetime.now().strftime("%H:%M:%S")
    st.caption(f"Update Terakhir: {waktu_sekarang} WIB")
    
    with st.spinner("Mengeksekusi TradingView Super-Engine... (1 Detik)"):
        try:
            # 1. Menarik SEMUA Data Saham IHSG dengan Filter Awal dari Server TradingView
            query = (Query()
                     .set_markets('indonesia')
                     .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 
                             'RSI', 'SMA50', 'MACD.macd', 'MACD.signal',
                             'open', 'high', 'low', 'market_cap_basic',
                             'price_book_ratio', 'return_on_equity')
                     .where(
                         Column('change') >= min_kenaikan,      # Naik %
                         Column('close') > Column('SMA50')      # Uptrend MA50
                     ))
            
            _, df = query.get_scanner_data()
            
            if not df.empty:
                # 2. Pemrosesan Data di Pandas (Lebih Canggih)
                # Filter Market Cap
                df = df[df['market_cap_basic'] >= min_mc_angka]
                
                # Filter Fundamental (PBV & ROE)
                if pakai_fundo:
                    df = df[(df['price_book_ratio'] <= max_pbv) & (df['return_on_equity'] >= min_roe)]
                
                # Filter Rasio Volume Lonjakan (Volume Hari Ini > x kali Rata-rata 10 Hari)
                df['vol_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0, 1)
                df = df[df['vol_ratio'] >= min_vol_ratio]
                
                # 3. ALGORITMA DETEKSI JEBAKAN (ANTI-TRAP)
                # Menghitung panjang ekor atas vs badan candle
                df['body'] = abs(df['close'] - df['open']).replace(0, 0.01)
                df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
                df['is_trap'] = df['upper_shadow'] > (2 * df['body'])
                
                # Urutkan berdasarkan kenaikan tertinggi
                df = df.sort_values('change', ascending=False).reset_index(drop=True)
                
                # --- MENAMPILKAN HASIL ---
                if not df.empty:
                    st.success(f"🔥 BINGO! Ditemukan {len(df)} Saham Jawara!")
                    
                    for index, row in df.iterrows():
                        with st.container():
                            saham = row['name']
                            naik = round(row['change'], 2)
                            st.markdown(f"### **{saham}** 📈 +{naik}%")
                            
                            # Status Bandar Anti-Trap
                            if row['is_trap']:
                                st.error("⚠️ HATI-HATI PUCUK (Ada Indikasi Guyuran Bandar / Ekor Atas Panjang)")
                            else:
                                st.success("✅ TARIKAN SOLID (Breakout MA50 Kuat)")
                                
                            # Tampilan Data Fundamental
                            st.write("**Fundamental & Valuasi:**")
                            mc_t = row['market_cap_basic'] / 1e12
                            c_f1, c_f2, c_f3 = st.columns(3)
                            c_f1.metric("Market Cap", f"Rp {mc_t:.1f} T")
                            c_f2.metric("PBV", f"{round(row['price_book_ratio'], 2)}x" if pd.notna(row['price_book_ratio']) else "N/A")
                            c_f3.metric("ROE", f"{round(row['return_on_equity'], 2)}%" if pd.notna(row['return_on_equity']) else "N/A")
                            
                            # Tampilan Data Teknikal
                            st.write("**Teknikal & Momentum:**")
                            c_t1, c_t2, c_t3 = st.columns(3)
                            c_t1.metric("Harga", f"Rp {int(row['close']):,}")
                            c_t2.metric("Vol Lonjak", f"{round(row['vol_ratio'], 1)}x")
                            warna_rsi = "🔴" if row['RSI'] > 70 else "🟢"
                            c_t3.metric(f"RSI {warna_rsi}", round(row['RSI'], 1))
                            
                            # Tampilkan Grafik dengan yfinance (Hanya dijalankan jika user mengeklik expander)
                            with st.expander("Lihat Grafik Candlestick vs MA50"):
                                gambar_grafik(saham)
                            
                            st.divider()
                else:
                    st.warning("Saham ada yang naik, namun gugur di filter Volume / Market Cap / Fundamental Anda.")
            else:
                st.warning("Tidak ada saham yang memenuhi kriteria di pasar saat ini.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan saat menghubungi server TradingView: {e}")

    # --- LOGIKA AUTO-SCAN 15 MENIT ---
    if mode_auto:
        st.info("Mode Auto-Scan Aktif. Layar jangan dikunci.")
        timer_placeholder = st.empty()
        
        for detik in range(900, 0, -1):
            menit, sisa_detik = divmod(detik, 60)
            timer_placeholder.markdown(f"### ⏳ Scan berikutnya dalam: **{menit:02d}:{sisa_detik:02d}**")
            time.sleep(1)
            
        st.rerun()