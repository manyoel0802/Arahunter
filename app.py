import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import warnings
import time
from datetime import datetime
from tradingview_screener import Query, Column

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

st.set_page_config(page_title="GOD MODE V38.0", layout="wide", page_icon="🎯")

try:
    TELE_TOKEN = st.secrets["TELE_TOKEN"]
    TELE_CHAT_ID = st.secrets["TELE_CHAT_ID"]
except:
    TELE_TOKEN = "8457858315:AAGPSHq0UsfPv8MZ733tHs40gAOxwvx7G0o"
    TELE_CHAT_ID = "5916986433"

if 'history_log' not in st.session_state:
    st.session_state['history_log'] = pd.DataFrame(columns=['Waktu', 'Ticker', 'Entry', 'Current_Price', 'High_Water_Mark', 'Trailing_SL', 'Status'])

st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-card { border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #30363d; color: white; }
    .bg-ultimate { background: linear-gradient(135deg, #020617 0%, #0f766e 50%, #0369a1 100%); border-top: 5px solid #06b6d4; box-shadow: 0 4px 20px rgba(6, 182, 212, 0.4); }
    .stock-card { background-color: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-top: 15px; border-left: 5px solid #06b6d4; }
    </style>
    """, unsafe_allow_html=True)

# --- 🎯 ULTIMATE ENGINES ---
def calculate_atr(df, period=14):
    try:
        tr = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        return tr.rolling(period).mean().iloc[-1]
    except: return 0.0

def detect_squeeze(df):
    try:
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
        df['Band_Width'] = (df['Upper'] - df['Lower']) / df['SMA20']
        
        current_bw = df['Band_Width'].iloc[-1]
        min_bw_month = df['Band_Width'].tail(20).min()
        return current_bw <= (min_bw_month * 1.1) 
    except: return False

def check_minervini_template(df):
    try:
        if len(df) < 200: return False
        c, sma50, sma150, sma200 = df['Close'].iloc[-1], df['Close'].rolling(50).mean().iloc[-1], df['Close'].rolling(150).mean().iloc[-1], df['Close'].rolling(200).mean().iloc[-1]
        return (c > sma150 and c > sma200 and sma150 > sma200 and sma50 > sma150 and c > sma50)
    except: return False

def check_smart_money(df):
    try:
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        return obv.iloc[-1] > obv.rolling(20).mean().iloc[-1]
    except: return False

# --- UI HEADER ---
st.markdown(f"""
<div class='status-card bg-ultimate'>
    <h1 style='margin:0; color:#22d3ee;'>🎯 GOD MODE V38.0: THE ULTIMATE SNIPER</h1>
    <p style='margin:5px 0 0 0; opacity:0.9; color:#e2e8f0;'>
        BB Squeeze | Adjustable Trailing Stop | Best Entry Zone | Timing Advisor
    </p>
</div>
""", unsafe_allow_html=True)

# --- 🎛️ SIDEBAR ---