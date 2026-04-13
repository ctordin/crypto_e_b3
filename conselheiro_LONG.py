import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conselheiro Crypto", layout="wide")

def buscar_dados_crypto(ticker, dias=180):
    try:
        # Busca dados históricos
        data = yf.download(ticker, period=f"{dias}d", interval="1d", progress=False)
        if data.empty:
            return None
        return data
    except:
        return None

def calcular_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Portfólio Crypto")
ticker_input = st.sidebar.text_input("Par (ex: AVAX-USD)", "AVAX-USD")
ja_possui = st.sidebar.checkbox("Já possuo esta moeda?")

preco_compra = st.sidebar.number_input("Preço de Compra ($)", format="%.4f")
stop_loss_max = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_calcular = st.sidebar.button("🚀 CALCULAR ESTRATÉGIA")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_calcular:
    df = buscar_dados_crypto(ticker_input)
    
    if df is not None:
        # Extração de métricas
        preco_atual = df['Close'].iloc[-1]
        volume_atual = df['Volume'].iloc[-1]
        volume_medio = df['Volume'].mean()
        rsi_valor = calcular_rsi(df)
        
        # --- NOVO: Cálculo de Máximas (90 e 180 dias) ---
        max_180d = df['High'].max()
        max_90d = df['High'].iloc[-90:].max()
        
        # Dashboard Superior
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Preço Atual", f"$ {preco_atual:.4f}")
        with col2:
            st.metric("RSI (Índice Força)", f"{rsi_valor:.1f}")
        with col3:
            vol_label = "Baixo" if volume_atual < volume_medio else "Alto"
            st.metric("Volume", vol_label)

        # --- Seção de Radiografia do Mercado ---
        st.subheader("📊 Radiografia do Mercado")
        
        # Exibição das Máximas Históricas Recentes
        c1, c2 = st.columns(2)
        c1.info(f"**Máxima 90 dias:** $ {max_90d:.4f}")
        c2.info(f"**Máxima 180 dias:** $ {max_180d:.4f}")

        # Lógica de Status
        if rsi_valor < 35:
            st.success("🟢 OPORTUNIDADE: Ativo sobrevendido. RSI baixo indica possível repique.")
        elif rsi_valor > 65:
            st.warning("🔴 ALERTA: Ativo sobrecomprado. Risco de correção alto.")
        else:
            st.info("🟡 NEUTRO: Aguarde uma definição de volume ou recuo no RSI.")

        # --- Gestão de Saída ---
        st.subheader("🛡️ Gestão de Saída")
        
        # Cálculo do Stop Loss baseado na configuração lateral
        valor_stop = preco_atual * (1 - (stop_loss_max / 100))
        alvo_sugerido = preco_atual * 1.20 # Alvo fixo de 20% para análise

        col_s1, col_s2 = st.columns(2)
        col_s1.error(f"Stop Loss Sugerido: $ {valor_stop:.4f}")
        col_s2.success(f"Alvo Sugerido (+20%): $ {alvo_sugerido:.4f}")
        
        # Alerta de Proximidade do Teto
        distancia_topo = ((max_180d - preco_atual) / max_180d) * 100
        st.write(f"**Análise de Ciclo:** O preço atual está a **{distancia_topo:.1f}%** abaixo da máxima dos últimos 180 dias.")

    else:
        st.error("Erro ao buscar dados. Verifique o ticker (ex: BTC-USD).")

else:
    st.write("Preencha os dados ao lado e clique em Calcular.")
