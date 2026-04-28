import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: B3 & Crypto", layout="wide")

def buscar_dados_hibrido(ticker, dias=180):
    ticker = ticker.upper().strip()
    
    # REGRA ESPECIAL PARA ZBT (Ticker problemático no Yahoo)
    if ticker == "ZBT":
        ticker = "ZBT1-USD"
    
    # REGRA PARA OUTRAS CRIPTOS (SOL, DOGE, AVAX...)
    elif "-" not in ticker and "." not in ticker:
        if not any(char.isdigit() for char in ticker):
            ticker = f"{ticker}-USD"
        else:
            # REGRA PARA B3 (PETR4, ALOS3...)
            ticker = f"{ticker}.SA"
            
    try:
        # Busca principal via Yahoo Finance (Mais estável)
        data = yf.download(ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True)
        if data.empty:
            return None, ticker
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data, ticker
    except:
        return None, ticker

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

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?", value=False)
preco_compra = st.sidebar.number_input("Meu Preço de Compra", format="%.4f", value=0.0)
btn_confirmar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Pro: Versão Híbrida")
st.divider()

if btn_confirmar:
    with st.spinner(f'Buscando {ticker_input}...'):
        df, ticker_final = buscar_dados_hibrido(ticker_input)
    
    if df is not None:
        # Preço e SMA 50 (Sua preferência)
        preco_atual = float(df['Close'].iloc[-1])
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_atual = float(df['SMA50'].iloc[-1])
        rsi_valor = float(calcular_rsi(df))
        
        # Dashboard
        col1, col2, col3 = st.columns(3)
        col1.metric(f"Preço Atual", f"$ {preco_atual:.4f}" if "-USD" in ticker_final else f"R$ {preco_atual:.2f}")
        col2.metric("SMA 50", f"{sma50_atual:.4f}")
        col3.metric("RSI (14d)", f"{rsi_valor:.1f}")

        # Análise de Tendência SMA 50
        if preco_atual > sma50_atual:
            st.success(f"📈 **Tendência de Alta:** Acima da SMA 50.")
        else:
            st.error(f"📉 **Tendência de Baixa:** Abaixo da SMA 50.")
            
        st.caption(f"Dados processados via: {ticker_final}")
    else:
        st.error(f"Não foi possível encontrar dados para '{ticker_input}'.")
