import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import time
import random
from datetime import datetime
from requests import Session

warnings.filterwarnings('ignore')

st.set_page_config(page_title="ARA Techno-Fund", layout="centered", page_icon="📈")

st.title("📈 Techno-Fundamental Hunter")
st.caption("Kombinasi Momentum ARA, Breakout MA50, dan Valuasi Murah (PBV & ROE)")

# --- KONFIGURASI SESI PALSU ---
sesi_palsu = Session()
sesi_palsu.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
})

# --- MEGA DATABASE SAHAM IHSG ---
DATABASE_SAHAM = """
AALI, ABBA, ABDA, ABMM, ACES, ACST, ADES, ADHI, AISA, AKKU, AKPI, AKRA, AKSI, ALDO, ALKA, ALMI, ALTO, AMAG, AMFG, AMIN, AMRT, ANJT, ANTM, APEX, APIC, APII, APLI, APLN, ARGO, ARII, ARNA, ARTA, ARTI, ARTO, ASBI, ASDM, ASGR, ASII, ASJT, ASMI, ASRI, ASRM, ASSA, ATIC, AUTO, BABP, BACA, BAJA, BALI, BAPA, BATA, BAYU, BBCA, BBHI, BBKP, BBLD, BBMD, BBNI, BBRI, BBRM, BBTN, BBYB, BCAP, BCIC, BCIP, BDMN, BEKS, BEST, BFIN, BGTG, BHIT, BIKA, BIMA, BINA, BIPI, BIPP, BIRD, BISI, BJBR, BJTM, BKDP, BKSL, BKSW, BLTA, BLTZ, BMAS, BMRI, BMSR, BMTR, BNBA, BNBR, BNGA, BNII, BNLI, BOLT, BPFI, BPII, BRAM, BRMS, BRNA, BRPT, BSDE, BSIM, BSSR, BSWD, BTEK, BTEL, BTON, BTPN, BUDI, BUKK, BULL, BUMI, BUVA, BVIC, BWPT, BYAN, CANI, CASS, CEKA, CENT, CFIN, CINT, CITA, CLPI, CMNP, CMPP, CNKO, CNTX, COWL, CPIN, CPRO, CSAP, CTBN, CTRA, CTTH, DART, DEFI, DEWA, DGIK, DILD, DKFT, DLTA, DMAS, DNAR, DNET, DOID, DPNS, DSFI, DSNG, DSSA, DUTI, DVLA, DYAN, ECII, EKAD, ELSA, ELTY, EMDE, EMTK, ENRG, EPMT, ERAA, ERTX, ESSA, ESTI, ETWA, EXCL, FAST, FASW, FISH, FMII, FORU, FPNI, GAMA, GDST, GDYR, GEMA, GEMS, GGRM, GIAA, GJTL, GLOB, GMTD, GOLD, GOLL, GPRA, GSMF, GTBO, GWSA, GZCO, HADE, HDFA, HERO, HEXA, HITS, HMSP, HOME, HOTL, HRUM, IATA, IBFN, IBST, ICBP, ICON, IGAR, IIKP, IKAI, IKBI, IMAS, IMJS, IMPC, INAF, INAI, INCI, INCO, INDF, INDR, INDS, INDX, INDY, INKP, INPC, INPP, INRU, INTA, INTD, INTP, IPOL, ISAT, ISSP, ITMA, ITMG, JAWA, JECC, JIHD, JKON, JPFA, JRPT, JSMR, JSPT, JTPE, KAEF, KARW, KBLI, KBLM, KBLV, KBRI, KDSI, KIAS, KICI, KIJA, KKGI, KLBF, KOBX, KOIN, KONI, KOPI, KPIG, KRAS, KREN, LAPD, LCGP, LEAD, LINK, LION, LMAS, LMPI, LMSH, LPCK, LPGI, LPIN, LPKR, LPLI, LPPF, LPPS, LRNA, LSIP, LTLS, MAGP, MAIN, MAPI, MAYA, MBAP, MBSS, MBTO, MCOR, MDIA, MDKA, MDLN, MDRN, MEDC, MEGA, MERK, META, MFMI, MGNA, MICE, MIDI, MIKA, MIRA, MITI, MKPI, MLBI, MLIA, MLPL, MLPT, MMLP, MNCN, MPMX, MPPA, MRAT, MREI, MSKY, MTDL, MTFN, MTLA, MTSM, MYOH, MYOR, MYTX, NELY, NIKL, NIRO, NISP, NOBU, NRCA, OCAP, OKAS, OMRE, PADI, PALM, PANR, PANS, PBRX, PDES, PEGE, PGAS, PGLI, PICO, PJAA, PKPK, PLAS, PLIN, PNBN, PNBS, PNIN, PNLF, PSAB, PSDN, PSKT, PTBA, PTIS, PTPP, PTRO, PTSN, PTSP, PUDP, PWON, PYFA, RAJA, RALS, RANC, RBMS, RDTX, RELI, RICY, RIGS, RIMO, RODA, ROTI, RUIS, SAFE, SAME, SCCO, SCMA, SCPI, SDMU, SDPC, SDRA, SGRO, SHID, SIDO, SILO, SIMA, SIMP, SIPD, SKBM, SKLT, SKYB, SMAR, SMBR, SMCB, SMDM, SMDR, SMGR, SMMA, SMMT, SMRA, SMRU, SMSM, SOCI, SONA, SPMA, SQMI, SRAJ, SRIL, SRSN, SRTG, SSIA, SSMS, SSTM, STAR, STTP, SUGI, SULI, SUPR, TALF, TARA, TAXI, TBIG, TBLA, TBMS, TCID, TELE, TFCO, TGKA, TIFA, TINS, TIRA, TIRT, TKIM, TLKM, TMAS, TMPO, TOBA, TOTL, TOTO, TOWR, TPIA, TPMA, TRAM, TRIL, TRIM, TRIO, TRIS, TRST, TRUS, TSPC, ULTJ, UNIC, UNIT, UNSP, UNTR, UNVR, VICO, VINS, VIVA, VOKS, VRNA, WAPO, WEHA, WICO, WIIM, WIKA, WINS, WOMF, WSKT, WTON, YPAS, YULE, ZBRA, SHIP, CASA, DAYA, DPUM, IDPR, JGLE, KINO, MARI, MKNT, MTRA, OASA, POWR, INCF, WSBP, PBSA, PRDA, BOGA, BRIS, PORT, CARS, MINA, CLEO, TAMU, CSIS, TGRA, FIRE, TOPS, KMTR, ARMY, MAPB, WOOD, HRTA, MABA, HOKI, MPOW, MARK, NASA, MDKI, BELL, KIOS, GMFI, MTWI, ZINC, MCAS, PPRE, WEGE, PSSI, MORA, DWGL, PBID, JMAS, CAMP, IPCM, PCAR, LCKM, BOSS, HELI, JSKY, INPS, GHON, TDPM, DFAM, NICK, BTPS, SPTO, PRIM, HEAL, TRUK, PZZA, TUGU, MSIN, SWAT, TNCA, MAPA, TCPI, IPCC, RISE, BPTR, POLL, NFCX, MGRO, NUSA, FILM, ANDI, LAND, MOLI, PANI, DIGI, CITY, SAPX, SURE, HKMU, MPRO, DUCK, GOOD, SKRN, YELO, CAKK, SATU, SOSS, DEAL, POLA, DIVA, LUCK, URBN, SOTS, ZONE, PEHA, FOOD, BEEF, POLI, CLAY, NATO, JAYA, COCO, MTPS, CPRI, HRME, POSA, JAST, FITT, BOLA, CCSI, SFAN, POLU, KJEN, KAYU, ITIC, PAMG, IPTV, BLUE, ENVY, EAST, LIFE, FUJI, KOTA, INOV, ARKA, SMKL, HDIT, KEEN, BAPI, TFAS, GGRP, OPMS, NZIA, SLIS, PURE, IRRA, DMMX, SINI, WOWS, ESIP, TEBE, KEJU, PSGO, AGAR, IFSH, REAL, IFII, PMJS, UCID, GLVA, PGJO, AMAR, CSRA, INDO, AMOR, TRIN, DMND, PURA, PTPW, TAMA, IKAN, SAMF, SBAT, KBAG, CBMF, RONY, CSMI, BBSS, BHAT, CASH, TECH, EPAC, UANG, PGUN, SOFA, PPGL, TOYS, SGER, TRJA, PNGO, SCNP, BBSI, KMDS, PURI, SOHO, HOMI, ROCK, ENZO, PLAN, PTDU, ATAP, VICI, PMMP, BANK, WMUU, EDGE, UNIQ, BEBS, SNLK, ZYRX, LFLO, FIMP, TAPG, NPGF, LUCY, ADCP, HOPE, MGLV, TRUE, LABA, ARCI, IPAC, MASB, BMHS, FLMC, NICL, UVCR, BUKA, HAIS, OILS, GPSO, MCOL, RSGK, RUNS, SBMA, CMNT, GTSI, IDEA, KUAS, BOBA, MTEL, DEPO, BINO, CMRY, WGSH, TAYS, WMPP, RMKE, OBMD, AVIA, IPPE, NASI, BSML, DRMA, ADMR, SEMA, ASLC, NETV, BAUT, ENAK, NTBK, SMKM, STAA, NANO, BIKE, WIRG, SICO, GOTO, TLDN, MTMH, WINR, IBOS, OLIV, ASHA, SWID, TRGU, ARKO, CHEM, DEWI, AXIO, KRYA, HATM, RCCC, GULA, JARR, AMMS, RAFI, KKES, ELPI, EURO, KLIN, TOOL, BUAH, CRAB, MEDS, COAL, PRAY, CBUT, BELI, MKTR, OMED, BSBK, PDPP, KDTN, ZATA, NINE, MMIX, PADA, ISAP, VTNY, SOUL, ELIT, BEER, CBPE, SUNI, CBRE, WINE, BMBL, PEVE, LAJU, FWCT, NAYZ, IRSX, PACK, VAST, CHIP, HALO, KING, PGEO, FUTR, HILL, BDKR, PTMP, SAGE, TRON, CUAN, NSSS, GTRA, HAJJ, JATI, TYRE, MPXL, SMIL, KLAS, MAXI, VKTR, RELF, AMMN, CRSN, GRPM, WIDI, TGUK, INET, MAHA, RMKO, CNMA, FOLK, HBAT, GRIA, PPRI, ERAL, CYBR, LMAX, HUMI, MSIE, RSCH, BABY, AEGS, IOTF, KOCI, PTPS, BREN, STRK, KOKA, LOPI, UDNG, RGAS, MSTI, IKPM, AYAM, SURI, ASLI, GRPH, SMGA, UNTD, TOSK, MPIX, ALII, MKAP, MEJA, LIVE, HYGN, BAIK, VISI, AREA, MHKI, ATLA, DATA, SOLA, BATR, SPRE, PART, GOLF, ISEA, BLES, GUNA, LABS, DOSS, NEST, PTMR, VERN, DAAZ, BOAT, NAIK, AADI, MDIY, KSIX, RATU, YOII, HGII, BRRC, DGWG, CBDK, OBAT, MINE, ASPR, PSAT, COIN, CDIA, BLOG, MERI, CHEK, PMUI, EMAS, PJHB, RLCO, SUPA, WBSA, KAQI, YUPI, FORE, MDLA, DKHH, AYLS, DADA, ASPI, ESTA, BESS, AMAN, CARE, PIPA, NCKL, MENN, AWAN, MBMA, RAAM, DOOH, CGAS, NICE, MSJA, SMLE, ACRO, MANG, WIFI, FAPA, DCII, KETR, DGNS, UFOE, ADMF, ADMG, ADRO, AGII, AGRO, AGRS, AHAP, AIMS, PNSE, POLY, POOL, PPRO
"""
list_saham = [s.strip().upper() for s in DATABASE_SAHAM.replace("\n", "").split(",") if s.strip()]

# --- FUNGSI TEKNIKAL ---
def hitung_indikator(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    # DITAMBAHKAN: MA50 untuk trend jangka menengah
    df['MA50'] = df['Close'].rolling(window=50).mean() 
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def cek_saham(ticker, min_kenaikan, min_vol, min_market_cap, max_pbv, min_roe, pakai_fundo):
    time.sleep(random.uniform(0.1, 0.4)) 
    try:
        t = f"{ticker}.JK" if not ticker.endswith('.JK') else ticker
        saham = yf.Ticker(t, session=sesi_palsu)
        
        # 1. FILTER MARKET CAP KILAT
        mc_value = 0
        mc_teks = "N/A"
        try:
            mc_value = saham.fast_info.get('marketCap', 0)
            if mc_value < min_market_cap: return None
            mc_teks = f"Rp {mc_value / 1e12:.1f} T"
        except: pass
        
        # 2. DATA HISTORIS (Ambil 3 bulan agar bisa menghitung MA50)
        df = saham.history(period="3mo") 
        if len(df) < 50: return None
        
        df = hitung_indikator(df)
        hari_ini, kemarin = df.iloc[-1], df.iloc[-2]
        
        kenaikan = ((hari_ini['Close'] - kemarin['Close']) / kemarin['Close']) * 100
        vol_kemarin = kemarin['Volume'] if kemarin['Volume'] > 0 else 1
        vol_ratio = hari_ini['Volume'] / vol_kemarin
        
        # 3. FILTER TEKNIKAL (Kenaikan, Volume, dan HARGA > MA50)
        if kenaikan >= min_kenaikan and vol_ratio >= min_vol and hari_ini['Close'] > hari_ini['MA50']:
            
            pbv_val, roe_val = "N/A", "N/A"
            pbv_lolos, roe_lolos = True, True
            
            # 4. FILTER FUNDAMENTAL (Dieksekusi HANYA jika lolos teknikal)
            if pakai_fundo:
                info = saham.info
                # Ambil data. Jika tidak ada, anggap tidak lolos (default angka ekstrim)
                pbv_raw = info.get('priceToBook', 999)
                roe_raw = info.get('returnOnEquity', -999) 
                
                if pbv_raw is None: pbv_raw = 999
                if roe_raw is None: roe_raw = -999
                
                # ROE di yfinance adalah desimal (0.15 = 15%)
                if pbv_raw > max_pbv: pbv_lolos = False
                if (roe_raw * 100) < min_roe: roe_lolos = False
                
                pbv_val = f"{round(pbv_raw, 2)}x" if pbv_raw != 999 else "Data Kosong"
                roe_val = f"{round(roe_raw * 100, 2)}%" if roe_raw != -999 else "Data Kosong"
            
            # Jika lolos semua saringan...
            if pbv_lolos and roe_lolos:
                o, c, h, l = hari_ini['Open'], hari_ini['Close'], hari_ini['High'], hari_ini['Low']
                body = abs(c - o)
                if body == 0: body = 0.01 
                upper_shadow = h - max(o, c)
                
                if upper_shadow > (2 * body):
                    status_bandar = "⚠️ HATI-HATI PUCUK (Ada Guyuran)"
                    warna_status = "red"
                else:
                    status_bandar = "✅ TARIKAN SOLID (Breakout MA50)"
                    warna_status = "green"

                return {
                    "Saham": ticker.replace('.JK', ''),
                    "Market Cap": mc_teks,
                    "Harga": f"Rp{int(hari_ini['Close']):,}",
                    "Naik (%)": round(kenaikan, 2),
                    "Vol(x)": round(vol_ratio, 1),
                    "PBV": pbv_val,
                    "ROE": roe_val,
                    "Data": df,
                    "RSI": round(hari_ini['RSI'], 2),
                    "Status": status_bandar,
                    "Warna Status": warna_status
                }
        return None
    except:
        return None

# --- UI APLIKASI ---
st.info(f"📊 Total Database: **{len(list_saham)} Saham** siap dipindai.")

with st.expander("⚙️ Buka Pengaturan Filter Lanjutan", expanded=True):
    st.subheader("1. Filter Kategori & Fundamental")
    pakai_fundo = st.checkbox("Aktifkan Filter PBV & ROE", value=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        opsi_mc = st.selectbox("Market Cap", ["Semua Ukuran", "Mulai Rp 500 M", "Mulai Rp 1 T", "Mulai Rp 10 T"])
    with col2:
        max_pbv = st.number_input("Max PBV (x)", value=2.0, step=0.5) if pakai_fundo else 999
    with col3:
        min_roe = st.number_input("Min ROE (%)", value=15.0, step=1.0) if pakai_fundo else -999

    st.subheader("2. Filter Teknikal & Momentum")
    st.caption("Secara otomatis memfilter saham yang Harga Saat Ini > MA50 (Uptrend).")
    col4, col5 = st.columns(2)
    with col4:
        min_kenaikan = st.number_input("Minimal Naik (%)", value=2.0, step=0.5)
    with col5:
        min_volume = st.number_input("Min Vol Loncat (x)", value=1.5, step=0.5)

# Konversi Market Cap
if "Semua Ukuran" in opsi_mc: min_mc_angka = 0
elif "500 M" in opsi_mc: min_mc_angka = 500_000_000_000
elif "1 T" in opsi_mc: min_mc_angka = 1_000_000_000_000
else: min_mc_angka = 10_000_000_000_000

st.divider()

# --- FITUR AUTO SCAN ---
col_btn, col_auto = st.columns([1, 1])
with col_btn:
    tombol_manual = st.button("🚀 SCAN SAHAM FUNDAMENTAL BAGUS SEKARANG", use_container_width=True, type="primary")
with col_auto:
    mode_auto = st.toggle("🔄 Auto-Scan (15 Menit)")

# --- LOGIKA EKSEKUSI ---
if tombol_manual or mode_auto:
    waktu_sekarang = datetime.now().strftime("%H:%M:%S")
    st.caption(f"Update Terakhir: {waktu_sekarang} WIB")
    
    hasil = []
    bar = st.progress(0)
    teks_status = st.empty()
    
    with st.spinner('Menyapu saham dengan algoritma Multi-Filter...'):
        total_saham = len(list_saham)
        ukuran_batch = 50 
        selesai = 0
        
        for i in range(0, total_saham, ukuran_batch):
            batch_saham = list_saham[i : i + ukuran_batch]
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(cek_saham, t, min_kenaikan, min_volume, min_mc_angka, max_pbv, min_roe, pakai_fundo): t for t in batch_saham}
                for f in as_completed(futures):
                    res = f.result()
                    if res: hasil.append(res)
                    
                    selesai += 1
                    bar.progress(selesai / total_saham)
                    teks_status.text(f"Memindai: {selesai} dari {total_saham} saham...")
            
            if i + ukuran_batch < total_saham:
                time.sleep(2) # Jeda anti-blokir
                
    bar.empty()
    teks_status.empty()
    
    # Menampilkan Hasil
    if hasil:
        hasil = sorted(hasil, key=lambda x: x['Naik (%)'], reverse=True)
        st.success(f"🔥 BINGO! {len(hasil)} Saham Fundamental Bagus Masuk Radar Momentum!")
        
        for item in hasil:
            with st.container():
                st.markdown(f"### **{item['Saham']}** 📈 +{item['Naik (%)']}%")
                
                # Header Status Bandar & Trend
                if item['Warna Status'] == "red":
                    st.error(item['Status'])
                else:
                    st.success(item['Status'])
                
                # Matrik Data Rapi
                st.write("**Data Fundamental:**")
                c_fund1, c_fund2, c_fund3 = st.columns(3)
                c_fund1.metric("Market Cap", item['Market Cap'])
                c_fund2.metric("Valuasi (PBV)", item['PBV'])
                c_fund3.metric("Kinerja (ROE)", item['ROE'])
                
                st.write("**Data Teknikal (Diatas MA50):**")
                c_tech1, c_tech2, c_tech3 = st.columns(3)
                c_tech1.metric("Harga", item['Harga'])
                c_tech2.metric("Vol Lonjak", f"{item['Vol(x)']}x")
                warna_rsi = "🔴" if item['RSI'] > 70 else "🟢"
                c_tech3.metric(f"RSI {warna_rsi}", item['RSI'])
                
                with st.expander("Lihat Grafik Candlestick vs MA50"):
                    df_chart = item['Data']
                    
                    # Tambahkan Garis MA50 ke dalam chart
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=df_chart.index[-60:], # Tampilkan 3 bulan terakhir agar MA50 jelas
                        open=df_chart['Open'][-60:], high=df_chart['High'][-60:],
                        low=df_chart['Low'][-60:], close=df_chart['Close'][-60:],
                        name="Harga"
                    ))
                    fig.add_trace(go.Scatter(
                        x=df_chart.index[-60:], y=df_chart['MA50'][-60:], 
                        line=dict(color='yellow', width=2), name='MA50 (Uptrend Support)'
                    ))
                    
                    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)
                st.divider()
    else:
        st.warning("Tidak ada saham yang memenuhi semua kriteria (Fundemantal Bagus + Uptrend MA50 + Volume Naik) hari ini.")

    # --- LOGIKA TIMER HITUNG MUNDUR ---
    if mode_auto:
        st.info("Mode Auto-Scan Aktif. Layar jangan dikunci.")
        timer_placeholder = st.empty()
        
        for detik in range(900, 0, -1):
            menit, sisa_detik = divmod(detik, 60)
            timer_placeholder.markdown(f"### ⏳ Scan berikutnya dalam: **{menit:02d}:{sisa_detik:02d}**")
            time.sleep(1)
            
        st.rerun()