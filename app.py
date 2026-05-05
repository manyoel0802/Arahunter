import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="ARA Hunter", layout="centered", page_icon="📱")

st.title("📱 ARA Hunter Mobile")
st.caption("Pantau potensi saham meroket langsung dari genggaman Anda.")

# --- FUNGSI TEKNIKAL ---
def hitung_indikator(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def cek_saham(ticker, min_kenaikan, min_vol):
    try:
        t = f"{ticker}.JK" if not ticker.endswith('.JK') else ticker
        saham = yf.Ticker(t)
        df = saham.history(period="3mo")
        if len(df) < 30: return None
        
        df = hitung_indikator(df)
        hari_ini, kemarin = df.iloc[-1], df.iloc[-2]
        
        kenaikan = ((hari_ini['Close'] - kemarin['Close']) / kemarin['Close']) * 100
        vol_kemarin = kemarin['Volume'] if kemarin['Volume'] > 0 else 1
        vol_ratio = hari_ini['Volume'] / vol_kemarin
        
        if kenaikan >= min_kenaikan and vol_ratio >= min_vol:
            return {
                "Saham": ticker.replace('.JK', ''),
                "Harga": f"Rp{int(hari_ini['Close']):,}",
                "Naik": f"{round(kenaikan, 2)}%",
                "Vol(x)": round(vol_ratio, 1),
                "MACD": "Bullish" if hari_ini['MACD'] > hari_ini['Signal'] else "Bearish",
                "Data": df,
                "RSI": round(hari_ini['RSI'], 2)
            }
        return None
    except:
        return None

# --- PENGATURAN DI LAYAR HP ---
with st.expander("⚙️ Buka Pengaturan Radar"):
    saham_default = "BBCA, GOTO, BREN, AMMN, CUAN, BRPT, PGO, TLKM, ASII, BMRI"
    input_teks = st.text_area("Kode Saham (koma):", saham_default)
    list_saham = [s.strip().upper() for s in input_teks.split(",")]
    
    col1, col2 = st.columns(2)
    with col1:
        min_kenaikan = st.number_input("Min Naik (%)", value=3)
    with col2:
        min_volume = st.number_input("Min Vol (x)", value=1.5)

# --- EKSEKUSI ---
if st.button("🚀 SCAN SEKARANG", use_container_width=True, type="primary"):
    if not list_saham:
        st.error("Isi kode saham dulu!")
    else:
        hasil = []
        bar = st.progress(0)
        
        with st.spinner('Menganalisis pasar...'):
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(cek_saham, t, min_kenaikan, min_volume): t for t in list_saham}
                for i, f in enumerate(as_completed(futures)):
                    res = f.result()
                    if res: hasil.append(res)
                    bar.progress((i + 1) / len(list_saham))
        
        bar.empty()
        
        if hasil:
            hasil = sorted(hasil, key=lambda x: float(x['Naik'].replace('%','')), reverse=True)
            st.success(f"🔥 {len(hasil)} Saham Ditemukan!")
            
            # Tampilan kartu (Card) yang lebih enak dibaca di HP daripada tabel panjang
            for item in hasil:
                with st.container():
                    st.markdown(f"### {item['Saham']} 📈 {item['Naik']}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Harga", item['Harga'])
                    c2.metric("Volume", f"{item['Vol(x)']}x")
                    c3.metric("RSI", item['RSI'])
                    
                    with st.expander("Lihat Grafik"):
                        df_chart = item['Data']
                        fig = go.Figure(data=[go.Candlestick(
                            x=df_chart.index[-30:], 
                            open=df_chart['Open'][-30:], high=df_chart['High'][-30:],
                            low=df_chart['Low'][-30:], close=df_chart['Close'][-30:]
                        )])
                        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig, use_container_width=True)
                    st.divider()
        else:
            st.warning("Tidak ada saham yang masuk radar saat ini.")