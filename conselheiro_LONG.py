import streamlit as st
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Universal Crypto", layout="wide")

@st.cache_data(ttl=3600)
def obter_lista_moedas():
    """Busca a lista de todas as moedas para mapear Ticker -> ID"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/list"
        response = requests.get(url)
        return pd.DataFrame(response.json())
    except:
        return pd.DataFrame()

def buscar_dados_universal(ticker, dias=180):
    ticker = ticker.lower().strip()
    moedas = obter_lista_moedas()
    
    if moedas.empty:
        return None

    # Tenta encontrar o ID pelo ticker (ex: sol, doge, zbt)
    try:
        coin_id = moedas[moedas['symbol'] == ticker]['id'].values[0]
    except:
        return None

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': dias, 'interval': 'daily'}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'Close'])
        df['Volume'] = [v[1] for v in data['total_volumes']]
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
st.sidebar.header("⚙️ Configurações")
ticker_input = st.sidebar.text_input("Digite o Ticker (ex: ZBT, SOL, DOGE)", "ZBT")

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?", value=False)
preco_analista = st.sidebar.number_input("Preço de Compra ($)", format="%.4f", value=0.0)
stop_loss_max = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_confirmar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Pro: Universal")
st.divider()

if btn_confirmar:
    with st.spinner(f'Buscando dados de {ticker_input.upper()}...'):
        df = buscar_dados_universal(ticker_input)
    
    if df is not None:
        preco_atual = float(df['Close'].iloc[-1])
        # SMA 50 (Sua preferência configurada)
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_atual = float(df['SMA50'].iloc[-1])
        
        rsi_serie = calcular_rsi(df['Close'])
        rsi_valor = float(rsi_serie.iloc[-1])
        
        # Dashboard
        col1, col2, col3 = st.columns(3)
        col1.metric(f"Preço {ticker_input.upper()}", f"$ {preco_atual:.4f}")
        col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col3.metric("SMA 50", f"$ {sma50_atual:.4f}")

        # Análise de Tendência
        if preco_atual > sma50_atual:
            st.success(f"📈 **Tendência de Alta:** O ativo está acima da SMA 50.")
        else:
            st.error(f"📉 **Tendência de Baixa:** O ativo está abaixo da SMA 50.")

        if rsi_valor > 65:
            st.warning("⚠️ Atenção: RSI indica sobrecompra.")
        elif rsi_valor < 35:
            st.success("✅ Atenção: RSI indica sobrevenda (Oportunidade).")

        # Gestão de Risco
        st.subheader("🛡️ Gestão de Risco")
        valor_stop = preco_atual * (1 - (stop_loss_max / 100))
        st.info(f"Stop Loss Sugerido para {ticker_input.upper()}: **$ {valor_stop:.4f}**")
    else:
        st.error(f"Erro: Não encontrei a moeda '{ticker_input}'. Verifique o ticker.")
