import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time
import requests
from datetime import datetime
from tradingview_screener import Query, Column

warnings = pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD TIER ARA Hunter", layout="wide", page_icon="👁️")

st.title("👁️ GOD TIER ARA Hunter (V10.0)")
st.caption("Sector Rotation | Smart Money Concepts (POC Support) | Master Algorithm | Telegram Alerts")

# --- UI PENGATURAN TELEGRAM ---
with st.sidebar:
    st.header("📲 Notifikasi Telegram")
    st.caption("Dapatkan sinyal otomatis saat radar menemukan saham VIP.")
    tele_token = st.text_input("Bot Token (dari BotFather)", type="password")
    tele_chat_id = st.text_input("Chat ID (dari @userinfobot)")
    aktifkan_tele = st.toggle("Aktifkan Alarm Telegram")

def kirim_telegram(pesan):
    if aktifkan_tele and tele_token and tele_chat_id:
        url = f"https://api.telegram.org/bot{tele_token}/sendMessage"
        payload = {"chat_id": tele_chat_id, "text": pesan, "parse_mode": "HTML"}
        try: requests.post(url, data=payload)
        except: pass

# --- UI PENGATURAN FILTER LENGKAP ---
with st.expander("⚙️ Buka Pengaturan Algoritma Utama", expanded=False):
    st.subheader("1. Algoritma Master Trader (Mark Minervini)")
    pakai_minervini = st.checkbox("Aktifkan Trend Template (Di atas MA200)", value=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        opsi_mc = st.selectbox("Market Cap", ["Semua", "Mulai Rp 500 M", "Mulai Rp 1 T", "Mulai Rp 10 T"], index=1)
    with col2:
        min_kenaikan = st.number_input("Minimal Naik Hari Ini (%)", value=2.0, step=0.5)
    with col3:
        min_vol_ratio = st.number_input("Min Vol Loncat (x Rata-rata)", value=1.5, step=0.5)

if "Semua" in opsi_mc: min_mc_angka = 0
elif "500 M" in opsi_mc: min_mc_angka = 500_000_000_000
elif "1 T" in opsi_mc: min_mc_angka = 1_000_000_000_000
else: min_mc_angka = 10_000_000_000_000

st.divider()

# --- TOMBOL EKSEKUSI ---
col_btn, col_auto = st.columns([2, 1])
with col_btn:
    tombol_manual = st.button("🚀 EKSEKUSI SUPER-ENGINE SEKARANG", use_container_width=True, type="primary")
with col_auto:
    mode_auto = st.toggle("🔄 Mode Auto-Scan & Alert (15 Menit)")

# --- FUNGSI MENGGAMBAR GRAFIK & SMART MONEY CONCEPTS (SMC) ---
def proses_chart_smc(ticker_bersih):
    try:
        saham = yf.Ticker(f"{ticker_bersih}.JK")
        df_chart = saham.history(period="6mo")
        df_chart['MA50'] = df_chart['Close'].rolling(window=50).mean()
        
        # ALGORITMA SMART MONEY: Menghitung POC (Point of Control) / Support Order Block
        # Mencari harga di mana volume transaksi paling masif terjadi dalam 6 bulan terakhir
        df_chart['Price_Bin'] = df_chart['Close'].round(-1)
        volume_profile = df_chart.groupby('Price_Bin')['Volume'].sum()
        poc_price = volume_profile.idxmax() # Inilah Support Terkuat (Order Block Institusi)
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_chart.index[-90:], open=df_chart['Open'][-90:], 
            high=df_chart['High'][-90:], low=df_chart['Low'][-90:], 
            close=df_chart['Close'][-90:], name="Harga"
        ))
        # Garis Tren
        fig.add_trace(go.Scatter(x=df_chart.index[-90:], y=df_chart['MA50'][-90:], line=dict(color='yellow', width=2), name='MA50'))
        
        # Garis Smart Money (Order Block Support)
        fig.add_trace(go.Scatter(
            x=[df_chart.index[-90], df_chart.index[-1]], y=[poc_price, poc_price],
            mode="lines", line=dict(color="cyan", width=3, dash="dot"), name=f"SMC Support (Rp {poc_price})"
        ))
        
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350, xaxis_rangeslider_visible=False, template="plotly_dark")
        return fig, poc_price
    except Exception as e:
        return None, 0

# --- LOGIKA EKSEKUSI TRADINGVIEW ---
if tombol_manual or mode_auto:
    waktu_sekarang = datetime.now().strftime("%H:%M:%S")
    st.caption(f"Update Terakhir: {waktu_sekarang} WIB")
    
    with st.spinner("Menarik Data Institusi (Rotasi Sektor, Momentum, Smart Money)..."):
        try:
            # 1. Menarik Data dengan Data Sektor
            query = (Query()
                     .set_markets('indonesia')
                     .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 
                             'RSI', 'SMA50', 'SMA200', 'price_52_week_high', 'price_52_week_low',
                             'open', 'high', 'low', 'market_cap_basic', 'sector')
                     .where(
                         Column('change') >= min_kenaikan,
                         Column('close') > Column('SMA50')
                     ))
            
            _, df = query.get_scanner_data()
            
            if not df.empty:
                # 2. Filter & Kalkulasi Dasar
                df = df[df['market_cap_basic'] >= min_mc_angka]
                df['vol_ratio'] = df['volume'] / df['average_volume_10d_calc'].replace(0, 1)
                df = df[df['vol_ratio'] >= min_vol_ratio]
                
                # 3. FITUR ROTASI SEKTORAL (TOP-DOWN APPROACH)
                st.subheader("📊 Peta Uang Berputar Hari Ini (Sector Rotation)")
                sektor_count = df['sector'].value_counts()
                top_sector = sektor_count.index[0] if not sektor_count.empty else "N/A"
                
                c_s1, c_s2 = st.columns(2)
                c_s1.metric("Leading Sector (Uang Terbanyak Masuk)", top_sector)
                c_s2.write(sektor_count.head(3))
                st.divider()
                
                # 4. Master Trader Algorithm & Anti-Trap
                if pakai_minervini:
                    df['jarak_52w_high'] = (df['close'] / df['price_52_week_high']) - 1
                    df['jarak_52w_low'] = (df['close'] / df['price_52_week_low']) - 1
                    df = df[
                        (df['close'] > df['SMA200']) & 
                        (df['SMA50'] > df['SMA200']) & 
                        (df['jarak_52w_high'] >= -0.25) & 
                        (df['jarak_52w_low'] >= 0.30)
                    ]
                
                df['body'] = abs(df['close'] - df['open']).replace(0, 0.01)
                df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
                df['is_trap'] = df['upper_shadow'] > (2 * df['body'])
                
                # 5. Probabilitas
                def hitung_probabilitas(row):
                    skor = 40 if pakai_minervini else 20
                    skor += min(row['vol_ratio'] * 10, 25)
                    skor += min(row['change'] * 2, 20)
                    if row['sector'] == top_sector: skor += 10 # Bonus jika saham berada di Top Sektor!
                    if 50 <= row['RSI'] <= 70: skor += 10
                    if row['is_trap']: skor -= 50 
                    else: skor += 10 
                    return max(1, min(int(skor), 99))
                
                if not df.empty:
                    df['prob_ara'] = df.apply(hitung_probabilitas, axis=1)
                    df = df.sort_values(by=['prob_ara', 'change'], ascending=[False, False]).reset_index(drop=True)
                
                # --- MENAMPILKAN HASIL & KIRIM TELEGRAM ---
                if not df.empty:
                    st.success(f"👁️ Ditemukan {len(df)} Saham Dewa!")
                    
                    pesan_telegram = f"🚨 <b>GOD TIER ALERTS</b> 🚨\nSektor Memimpin: {top_sector}\n\n"
                    
                    for index, row in df.iterrows():
                        saham = row['name']
                        naik = round(row['change'], 2)
                        harga = int(row['close'])
                        
                        # Hanya memproses chart (SMC) untuk Top 5 agar tidak lemot
                        fig, poc_price = None, 0
                        if index < 5: 
                            fig, poc_price = proses_chart_smc(saham)
                        
                        # Siapkan pesan Telegram
                        if index < 3 and not row['is_trap']: # Kirim max 3 saham terbaik yg aman
                            pesan_telegram += f"💎 <b>{saham}</b> (+{naik}%)\nVol: {round(row['vol_ratio'],1)}x | Support SMC: Rp {poc_price}\n\n"
                        
                        # UI Streamlit
                        with st.container():
                            st.markdown(f"### Rank #{index+1}: **{saham}** 📈 +{naik}% (Sektor: {row['sector']})")
                            
                            prob = row['prob_ara']
                            st.progress(prob / 100, text=f"Skor Algoritma Institusi: {prob}%")
                            
                            c_t1, c_t2, c_t3, c_t4 = st.columns(4)
                            c_t1.metric("Harga Terakhir", f"Rp {harga:,}")
                            c_t2.metric("Support Institusi (SMC)", f"Rp {int(poc_price):,}" if poc_price else "N/A")
                            c_t3.metric("Jarak Tembus Pucuk", f"{round(((row['close'] / row['price_52_week_high']) - 1) * 100, 2)}%")
                            c_t4.metric("Uang Besar (Volume)", f"{round(row['vol_ratio'], 1)}x Lipat")
                            
                            if row['is_trap']: st.error("⚠️ Peringatan: Terdeteksi Distribusi / Ekor Atas Panjang")
                            else: st.success("✅ Terdeteksi Akumulasi Institusi (Breakout Bersih)")
                            
                            if fig:
                                with st.expander("Lihat Peta Support Smart Money (Garis Cyan)"):
                                    st.plotly_chart(fig, use_container_width=True)
                            st.divider()
                    
                    # Eksekusi Kirim Telegram
                    if aktifkan_tele:
                        kirim_telegram(pesan_telegram)
                        st.sidebar.success("Sinyal telah dikirim ke Telegram Anda!")
                        
                else:
                    st.warning("Saham berguguran di filter algoritma kelas berat ini.")
            else:
                st.warning("Tidak ada data pasar saat ini.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis: {e}")

    # --- LOGIKA AUTO-SCAN TIMER ---
    if mode_auto:
        timer_placeholder = st.empty()
        for detik in range(900, 0, -1):
            menit, sisa_detik = divmod(detik, 60)
            timer_placeholder.markdown(f"### ⏳ Menunggu Radar Berikutnya: **{menit:02d}:{sisa_detik:02d}**")
            time.sleep(1)
        st.rerun()