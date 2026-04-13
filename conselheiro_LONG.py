import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conselheiro Crypto", layout="wide")

def buscar_dados_crypto(ticker, dias=180):
    try:
        # Busca dados históricos
        # Usamos auto_adjust=True para garantir que as colunas sejam consistentes
        data = yf.download(ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True)
        
        if data.empty or len(data) < 2:
            return None
        return data
    except Exception as e:
        return None

def calcular_rsi(data, window=14):
    # Garante que estamos usando apenas a coluna Close como Series
    close = data['Close'].squeeze()
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Portfólio Crypto")
ticker_input = st.sidebar.text_input("Par (ex: AVAX-USD)", "AVAX-USD")
ja_possui = st.sidebar.checkbox("Já possuo esta moeda?")

preco_compra = st.sidebar.number_input("Preço de Compra ($)", format="%.4f", value=0.0)
stop_loss_max = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_calcular = st.sidebar.button("🚀 CALCULAR ESTRATÉGIA")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_calcular:
    with st.spinner('Buscando dados do mercado...'):
        df = buscar_dados_crypto(ticker_input)
    
    if df is not None:
        try:
            # .item() ou float() garante que pegamos o valor numérico puro, 
            # evitando erros de Series/Dataframe no st.metric
            preco_atual = float(df['Close'].iloc[-1])
            volume_atual = float(df['Volume'].iloc[-1])
            volume_medio = float(df['Volume'].mean())
            rsi_valor = float(calcular_rsi(df))
            
            # Máximas
            max_180d = float(df['High'].max())
            max_90d = float(df['High'].iloc[-90:].max() if len(df) >= 90 else df['High'].max())
            
            # Dashboard Superior
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Preço Atual", f"$ {preco_atual:.4f}")
            with col2:
                st.metric("RSI (Índice Força)", f"{rsi_valor:.1f}")
            with col3:
                vol_label = "Baixo" if volume_atual < volume_medio else "Alto"
                st.metric("Volume", vol_label)

            # --- Radiografia do Mercado ---
            st.subheader("📊 Radiografia do Mercado")
            
            c1, c2 = st.columns(2)
            c1.info(f"**Máxima 90 dias:** $ {max_90d:.4f}")
            c2.info(f"**Máxima 180 dias:** $ {max_180d:.4f}")

            if rsi_valor < 35:
                st.success("🟢 OPORTUNIDADE: Ativo sobrevendido (RSI Baixo).")
            elif rsi_valor > 65:
                st.warning("🔴 ALERTA: Ativo sobrecomprado (RSI Alto).")
            else:
                st.info("🟡 NEUTRO: Aguarde uma definição de volume ou recuo no RSI.")

            # --- Gestão de Saída ---
            st.subheader("🛡️ Gestão de Saída")
            
            valor_stop = preco_atual * (1 - (stop_loss_max / 100))
            alvo_sugerido = preco_atual * 1.20

            col_s1, col_s2 = st.columns(2)
            col_s1.error(f"Stop Loss Sugerido: $ {valor_stop:.4f}")
            col_s2.success(f"Alvo Sugerido (+20%): $ {alvo_sugerido:.4f}")
            
            distancia_topo = ((max_180d - preco_atual) / max_180d) * 100
            st.write(f"**Análise de Ciclo:** O preço atual está a **{distancia_topo:.1f}%** abaixo da máxima dos últimos 180 dias.")

        except Exception as e:
            st.error(f"Erro ao processar valores: {e}")
    else:
        st.error("Ticker não encontrado ou sem dados. Use o formato 'AVAX-USD'.")

else:
    st.write("Configure os parâmetros na lateral e clique em Calcular.")
