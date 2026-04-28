import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Híbrido", layout="wide")

def resgate_coingecko(ticker):
    """Busca o ID correto e os dados se o Yahoo falhar"""
    ticker_map = {"ZBT": "zerobase", "ZBT1": "zerobase"}
    coin_id = ticker_map.get(ticker.upper(), ticker.lower())
    
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': '180', 'interval': 'daily'}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'Close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except:
        return None

def buscar_dados_perfeitos(ticker, dias=180):
    original = ticker.upper().strip()
    
    # 1. Formatação para Yahoo (SOL, DOGE, PETR4)
    y_ticker = original
    if "-" not in y_ticker and "." not in y_ticker:
        if not any(char.isdigit() for char in y_ticker):
            y_ticker = f"{y_ticker}-USD"
        else:
            y_ticker = f"{y_ticker}.SA"
            
    try:
        data = yf.download(y_ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data, f"Yahoo ({y_ticker})"
    except:
        pass
    
    # 2. Resgate automático para ZBT ou falhas do Yahoo
    data_resgate = resgate_coingecko(original)
    if data_resgate is not None:
        return data_resgate, f"CoinGecko ({original})"
    
    return None, original

def calcular_rsi(data, window=14):
    close = data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 0.001)
    return (100 - (100 / (1 + rs))).iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Configurações")
ticker_input = st.sidebar.text_input("Ativo (ZBT, SOL, PETR4...)", "ZBT")
btn_confirmar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Pro: B3 & Crypto")

if btn_confirmar:
    with st.spinner(f'Consultando bases de dados para {ticker_input}...'):
        df, fonte = buscar_dados_perfeitos(ticker_input)
    
    if df is not None:
        preco_atual = float(df['Close'].iloc[-1])
        # SMA 50 (Sua preferência configurada)
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_atual = float(df['SMA50'].iloc[-1])
        rsi_valor = float(calcular_rsi(df))
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Preço Atual", f"$ {preco_atual:.4f}")
        col2.metric("SMA 50", f"{sma50_atual:.4f}")
        col3.metric("RSI (14d)", f"{rsi_valor:.1f}")

        # Análise de Tendência SMA 50
        if preco_atual > sma50_atual:
            st.success(f"📈 **Tendência de Alta:** Acima da SMA 50.")
        else:
            st.error(f"📉 **Tendência de Baixa:** Abaixo da SMA 50.")
            
        st.caption(f"Fonte utilizada: {fonte}")
    else:
        st.error(f"Não foi possível encontrar dados para '{ticker_input}'.")
