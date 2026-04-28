import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: B3 & Crypto", layout="wide")

def buscar_dados_crypto_gecko(asset_id="zerobase", days=180):
    """Busca dados diretamente da CoinGecko para evitar erros do Yahoo Finance"""
    url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': days, 'interval': 'daily'}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        prices = data['prices']
        volumes = data['total_volumes']
        
        df = pd.DataFrame(prices, columns=['timestamp', 'Close'])
        df['Volume'] = [v[1] for v in volumes]
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except:
        return None

def calcular_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 0.001)
    return 100 - (100 / (1 + rs))

# --- Interface Lateral ---
st.sidebar.header("⚙️ Configurações de Análise")
# Note: o ID na CoinGecko para o ZBT é 'zerobase'
ticker_input = st.sidebar.selectbox("Selecione o Ativo", ["ZBT (Zerobase)", "Bitcoin", "Ethereum"])
asset_map = {"ZBT (Zerobase)": "zerobase", "Bitcoin": "bitcoin", "Ethereum": "ethereum"}

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?", value=False)
preco_analista = st.sidebar.number_input("Meu Preço de Compra ($)", format="%.4f", value=0.0)
stop_loss_max = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_confirmar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Pro: Foco em Crypto")
st.divider()

if btn_confirmar:
    with st.spinner('Acessando API da CoinGecko...'):
        df = buscar_dados_crypto_gecko(asset_map[ticker_input])
    
    if df is not None:
        # Cálculos Técnicos
        preco_atual = float(df['Close'].iloc[-1])
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_atual = float(df['SMA50'].iloc[-1])
        rsi_serie = calcular_rsi(df['Close'])
        rsi_valor = float(rsi_serie.iloc[-1])
        
        # Dashboard
        col1, col2, col3 = st.columns(3)
        col1.metric("Preço Atual (USD)", f"$ {preco_atual:.4f}")
        col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col3.metric("SMA 50", f"$ {sma50_atual:.4f}")

        # Análise de Tendência (SMA 50)
        if preco_atual > sma50_atual:
            st.success(f"📈 **Tendência de Alta:** Acima da SMA 50.")
        else:
            st.error(f"📉 **Tendência de Baixa:** Abaixo da SMA 50.")

        # Gestão de Risco
        st.subheader("🛡️ Gestão de Risco")
        valor_stop = preco_atual * (1 - (stop_loss_max / 100))
        st.warning(f"Seu Stop Loss deve estar em: **$ {valor_stop:.4f}**")

    else:
        st.error("Erro ao conectar com a API de Crypto. Tente novamente em instantes.")
