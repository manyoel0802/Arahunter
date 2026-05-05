import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="ARA Hunter V3", layout="centered", page_icon="🔥")

st.title("🔥 ARA Hunter V3 (Auto-Data)")
st.caption("Pantau potensi ARA dari 150+ Saham Paling Aktif di IHSG dengan satu klik.")

# --- DATABASE SAHAM OTOMATIS (150+ Saham Liquid & Aktif IHSG) ---
DATABASE_SAHAM = """
BBCA,BBRI,BMRI,BBNI,BRIS,NISP,PNLF,ARTO,BBYB,BBTN,BDMN,
GOTO,BUKA,EMTK,WIFI,ISAT,EXCL,TLKM,TOWR,TBIG,
BREN,AMMN,CUAN,BRPT,PGEO,ADRO,PTBA,ITMG,HRUM,MEDC,ENRG,ELSA,AKRA,INDY,DOID,BUMI,DEWA,BRMS,
INCO,ANTM,MDKA,MBMA,NCKL,TINS,
ASII,UNTR,AUTO,SMSM,
ICBP,INDF,MYOR,AMRT,MIDI,CPIN,JPFA,CMRY,CLEO,
KLBF,SIDO,SILO,MIKA,HEAL,
PANI,BSDE,CTRA,SMRA,PWON,ASRI,BSBK,
WIKA,PTPP,ADHI,WEGE,PSSI,JSMR,CMNP,
INKP,TKIM,TPIA,ESSA,SMGR,INTP,
FILM,RAAM,CNMA,MSIN,MNCN,SCMA,
VKTR,GEMS,BSSR,SSIA,SMMT,TPMA,HAIS,SMDR,TMAS,CARS,
OASA,KEEN,ARKO,CGAS,MUTU,
DATA,CHIP,HALO,AWAN,
CGAT,STRK,INET,AEGS,MSKY,SAGE,GTRA,DOOH,CRSN,KAYU,JARR,
GULA,TGUK,SOUL,TRON,OMED,KAEF,PEHA,IRRA,
PENG,NELY,MAPI,MAPA,ACES,ERA,ERAA
"""

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
        df = saham.history(period="2mo") # Dipersingkat jadi 2 bulan agar download lebih cepat
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
                "Naik (%)": round(kenaikan, 2),
                "Vol(x)": round(vol_ratio, 1),
                "MACD": "Bullish" if hari_ini['MACD'] > hari_ini['Signal'] else "Bearish",
                "Data": df,
                "RSI": round(hari_ini['RSI'], 2)
            }
        return None
    except:
        return None

# --- UI APLIKASI ---
# Opsi Pemilihan Data
pilihan_mode = st.radio("Pilih Mode Pemindaian:", ["Otomatis (Top 150+ Saham Aktif)", "Manual (Ketik Sendiri)"], horizontal=True)

if pilihan_mode == "Otomatis (Top 150+ Saham Aktif)":
    list_saham = [s.strip().upper() for s in DATABASE_SAHAM.replace("\n", "").split(",")]
    st.info(f"Database aktif: **{len(list_saham)} Saham** siap dipindai.")
else:
    input_teks = st.text_area("Ketik Kode Saham (pisahkan koma):", "BBCA, GOTO, BREN, AMMN")
    list_saham = [s.strip().upper() for s in input_teks.split(",")]

# Pengaturan Filter
with st.expander("⚙️ Atur Filter Ketat (Opsional)"):
    col1, col2 = st.columns(2)
    with col1:
        min_kenaikan = st.number_input("Min Naik (%)", value=3)
    with col2:
        min_volume = st.number_input("Min Vol (x lipat)", value=1.5)

# --- EKSEKUSI UTAMA ---
if st.button("🚀 SCAN PASAR SEKARANG", use_container_width=True, type="primary"):
    if not list_saham or list_saham == ['']:
        st.error("Daftar saham tidak boleh kosong!")
    else:
        hasil = []
        bar = st.progress(0)
        teks_status = st.empty()
        
        with st.spinner(f'Menganalisis {len(list_saham)} saham... Jangan tutup layar.'):
            # Menggunakan 15 pekerja agar lebih cepat
            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = {executor.submit(cek_saham, t, min_kenaikan, min_volume): t for t in list_saham}
                for i, f in enumerate(as_completed(futures)):
                    res = f.result()
                    if res: hasil.append(res)
                    bar.progress((i + 1) / len(list_saham))
                    teks_status.text(f"Mengecek saham ke-{i+1}...")
        
        bar.empty()
        teks_status.empty()
        
        if hasil:
            hasil = sorted(hasil, key=lambda x: x['Naik (%)'], reverse=True)
            st.success(f"🔥 BINGO! {len(hasil)} Saham Masuk Radar")
            
            for item in hasil:
                with st.container():
                    # Menampilkan header saham dengan persentase kenaikan
                    st.markdown(f"### **{item['Saham']}** 📈 +{item['Naik (%)']}%")
                    
                    # Layout metrik yang rapi untuk layar HP
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Harga", item['Harga'])
                    c2.metric("Vol Lonjak", f"{item['Vol(x)']}x")
                    
                    # Warna RSI (Overbought/Normal)
                    warna_rsi = "🔴" if item['RSI'] > 70 else "🟢"
                    c3.metric(f"RSI {warna_rsi}", item['RSI'])
                    
                    with st.expander(f"Lihat Grafik & Detail MACD: {item['MACD']}"):
                        df_chart = item['Data']
                        fig = go.Figure(data=[go.Candlestick(
                            x=df_chart.index[-30:], # Menampilkan 1 bulan terakhir agar jelas di HP
                            open=df_chart['Open'][-30:], high=df_chart['High'][-30:],
                            low=df_chart['Low'][-30:], close=df_chart['Close'][-30:]
                        )])
                        fig.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0), 
                            height=250, 
                            xaxis_rangeslider_visible=False,
                            template="plotly_dark"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    st.divider()
        else:
            st.warning("Pasar sedang lesu atau filter terlalu ketat. Tidak ada saham yang masuk radar hari ini.")