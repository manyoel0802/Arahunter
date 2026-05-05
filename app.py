import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime
from tradingview_screener import Query, Column

warnings = pd.options.mode.chained_assignment = None

st.set_page_config(page_title="Master ARA Hunter", layout="centered", page_icon="🦅")

st.title("🦅 Master ARA Hunter (V9.0)")
st.caption("Menggunakan Algoritma Trader Legendaris (Mark Minervini & William O'Neil)")

# --- UI PENGATURAN FILTER ---
with st.expander("⚙️ Buka Pengaturan Filter Lanjutan", expanded=True):
    st.subheader("1. Algoritma Master Trader (Mark Minervini)")
    pakai_minervini = st.checkbox("Aktifkan 'Minervini Trend Template' (Sangat Disarankan)", value=True)
    st.caption("Hanya mencari saham yang berada dalam fase Uptrend Super Kuat (Di atas MA200, dekat dengan titik tertinggi 52-minggu).")
    
    st.subheader("2. Filter Valuasi (Warren Buffett / Value Investing)")
    pakai_fundo = st.checkbox("Aktifkan Filter Valuasi (PBV & ROE)", value=False)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        opsi_mc = st.selectbox("Market Cap", ["Semua Ukuran", "Mulai Rp 500 M", "Mulai Rp 1 T", "Mulai Rp 10 T"], index=1)
    with col2:
        max_pbv = st.number_input("Max PBV (x)", value=3.0, step=0.5) if pakai_fundo else 999
    with col3:
        min_roe = st.number_input("Min ROE (%)", value=10.0, step=1.0) if pakai_fundo else -999

    st.subheader("3. Filter Momentum Harian")
    col4, col5 = st.columns(2)
    with col4:
        min_kenaikan = st.number_input("Minimal Naik Hari Ini (%)", value=2.0, step=0.5)
    with col5:
        min_vol_ratio = st.number_input("Min Vol Loncat (x Rata-rata)", value=1.5, step=0.5)

# Konversi Market Cap
if "Semua Ukuran" in opsi_mc: min_mc_angka = 0
elif "500 M" in opsi_mc: min_mc_angka = 500_000_000_000
elif "1 T" in opsi_mc: min_mc_angka = 1_000_000_000_000
else: min_mc_angka = 10_000_000_000_000

st.divider()

# --- FITUR AUTO SCAN ---
col_btn, col_auto = st.columns([1, 1])
with col_btn:
    tombol_manual = st.button("🚀 SCAN DENGAN ALGORITMA MASTER SEKARANG", use_container_width=True, type="primary")
with col_auto:
    mode_auto = st.toggle("🔄 Auto-Scan (15 Menit)")

# --- FUNGSI MENGGAMBAR GRAFIK (YFINANCE) ---
def gambar_grafik(ticker_bersih):
    try:
        saham = yf.Ticker(f"{ticker_bersih}.JK")
        df_chart = saham.history(period="6mo") # Diperpanjang jadi 6 bulan untuk melihat MA200
        df_chart['MA50'] = df_chart['Close'].rolling(window=50).mean()
        df_chart['MA200'] = df_chart['Close'].rolling(window=200).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_chart.index[-90:], open=df_chart['Open'][-90:], 
            high=df_chart['High'][-90:], low=df_chart['Low'][-90:], 
            close=df_chart['Close'][-90:], name="Harga"
        ))
        fig.add_trace(go.Scatter(x=df_chart.index[-90:], y=df_chart['MA50'][-90:], line=dict(color='yellow', width=2), name='MA50'))
        fig.add_trace(go.Scatter(x=df_chart.index[-90:], y=df_chart['MA200'][-90:], line=dict(color='purple', width=2), name='MA200 (Long Trend)'))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.caption("Data grafik belum tersedia.")

# --- LOGIKA EKSEKUSI TRADINGVIEW ---
if tombol_manual or mode_auto:
    waktu_sekarang = datetime.now().strftime("%H:%M:%S")
    st.caption(f"Update Terakhir: {waktu_sekarang} WIB")
    
    with st.spinner("Menjalankan Algoritma Master Trader..."):
        try:
            # 1. Menarik Data dengan Kolom Tambahan (MA200, 52W High, 52W Low)
            query = (Query()
                     .set_markets('indonesia')
                     .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 
                             'RSI', 'SMA50', 'SMA200', 'price_52_week_high', 'price_52_week_low',
                             'MACD.macd', 'MACD.signal', 'open', 'high', 'low', 'market_cap_basic',
                             'price_book_ratio', 'return_on_equity')
                     .where(
                         Column('change') >= min_kenaikan,
                         Column('close') > Column('SMA50')
                     ))
            
            _, df = query.get_scanner_data()
            
            if not df.empty:
                # 2. Filter Market Cap & Fundamental
                df = df[df['market_cap_basic'] >= min_mc_angka]
                if pakai_fundo:
                    df = df[(df['price_book_ratio'] <= max_pbv) & (df['return_on_equity'] >= min_roe)]
                
                # 3. Filter Rasio Volume
                df['vol_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0, 1)
                df = df[df['vol_ratio'] >= min_vol_ratio]
                
                # 4. ALGORITMA MASTER TRADER (MARK MINERVINI TREND TEMPLATE)
                if pakai_minervini:
                    df['jarak_52w_high'] = (df['close'] / df['price_52_week_high']) - 1
                    df['jarak_52w_low'] = (df['close'] / df['price_52_week_low']) - 1
                    
                    df = df[
                        (df['close'] > df['SMA200']) &            # Harga di atas MA200
                        (df['SMA50'] > df['SMA200']) &            # MA50 di atas MA200
                        (df['jarak_52w_high'] >= -0.25) &         # Maksimal 25% dari puncak 52-minggu
                        (df['jarak_52w_low'] >= 0.30)             # Minimal sudah naik 30% dari dasar 52-minggu
                    ]
                
                # 5. Algoritma Anti-Trap
                df['body'] = abs(df['close'] - df['open']).replace(0, 0.01)
                df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
                df['is_trap'] = df['upper_shadow'] > (2 * df['body'])
                
                # 6. Algoritma Probabilitas Super
                def hitung_probabilitas(row):
                    skor = 40 if pakai_minervini else 20
                    skor += min(row['vol_ratio'] * 10, 25)
                    skor += min(row['change'] * 2, 20)
                    if 50 <= row['RSI'] <= 70: skor += 15
                    elif 70 < row['RSI'] <= 85: skor += 5
                    
                    if row['is_trap']: skor -= 50 
                    else: skor += 10 
                    return max(1, min(int(skor), 99))
                
                if not df.empty:
                    df['prob_ara'] = df.apply(hitung_probabilitas, axis=1)
                    df = df.sort_values(by='prob_ara', ascending=False).reset_index(drop=True)
                
                # --- MENAMPILKAN HASIL ---
                if not df.empty:
                    st.success(f"🦅 Ditemukan {len(df)} Saham yang Memenuhi Standar Master Trader Dunia!")
                    
                    for index, row in df.iterrows():
                        with st.container():
                            saham = row['name']
                            naik = round(row['change'], 2)
                            
                            ranking = index + 1
                            medali = "👑" if ranking == 1 else ("💎" if ranking <= 3 else "📌")
                            
                            st.markdown(f"### {medali} Rank #{ranking}: **{saham}** 📈 +{naik}%")
                            
                            prob = row['prob_ara']
                            if prob >= 80:
                                st.progress(prob / 100, text=f"🔥 Super Setup: Probabilitas Breakout {prob}%")
                            elif prob >= 50:
                                st.progress(prob / 100, text=f"⚡ Setup Standar: Probabilitas Breakout {prob}%")
                            else:
                                st.progress(prob / 100, text=f"⚠️ Risiko Tinggi: Terindikasi Guyuran/Trap {prob}%")
                            
                            if row['is_trap']:
                                st.error("⚠️ STATUS BANDAR: Guyuran Terdeteksi (Jarum Atas Panjang)")
                            else:
                                st.success("✅ STATUS BANDAR: Akumulasi Kuat / Breakout Valid")
                                
                            # Tampilan Data Lengkap
                            st.write("**Posisi Trend (Minervini Data):**")
                            c_m1, c_m2, c_m3 = st.columns(3)
                            jarak_puncak = round(((row['close'] / row['price_52_week_high']) - 1) * 100, 2)
                            c_m1.metric("Jarak ke ATH (52W)", f"{jarak_puncak}%")
                            c_m2.metric("Harga vs MA50", "Di atas MA50" if row['close'] > row['SMA50'] else "Di bawah MA50")
                            c_m3.metric("MA50 vs MA200", "Uptrend" if row['SMA50'] > row['SMA200'] else "Downtrend")
                            
                            st.write("**Teknikal Harian:**")
                            c_t1, c_t2, c_t3 = st.columns(3)
                            c_t1.metric("Harga", f"Rp {int(row['close']):,}")
                            c_t2.metric("Vol Lonjak", f"{round(row['vol_ratio'], 1)}x")
                            warna_rsi = "🔴" if row['RSI'] > 70 else "🟢"
                            c_t3.metric(f"RSI {warna_rsi}", round(row['RSI'], 1))
                            
                            with st.expander("Lihat Grafik MA50 (Kuning) & MA200 (Ungu)"):
                                gambar_grafik(saham)
                            
                            st.divider()
                else:
                    st.warning("Saham yang naik hari ini GAGAL memenuhi syarat ketat Master Trader (Trend belum kuat).")
            else:
                st.warning("Tidak ada saham yang memenuhi kriteria di pasar saat ini.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")

    # --- LOGIKA AUTO-SCAN 15 MENIT ---
    if mode_auto:
        st.info("Mode Auto-Scan Aktif. Layar jangan dikunci.")
        timer_placeholder = st.empty()
        
        for detik in range(900, 0, -1):
            menit, sisa_detik = divmod(detik, 60)
            timer_placeholder.markdown(f"### ⏳ Scan berikutnya dalam: **{menit:02d}:{sisa_detik:02d}**")
            time.sleep(1)
            
        st.rerun()