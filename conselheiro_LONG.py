import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conselheiro Crypto", layout="wide")

def buscar_dados_crypto(ticker, dias=180):
    try:
        data = yf.download(ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except Exception:
        return None

def calcular_rsi(data, window=14):
    close = data['Close'].iloc[:, 0] if len(data['Close'].shape) > 1 else data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 0.001)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# --- Interface Lateral (RESTAURADA) ---
st.sidebar.header("⚙️ Configurações de Análise")
ticker_input = st.sidebar.text_input("Par (ex: AVAX-USD)", "AVAX-USD")

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo esta moeda?", value=False)
preco_analista = st.sidebar.number_input("Preço de Compra / Analista ($)", format="%.4f", value=0.0)
stop_loss_max = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_confirmar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_confirmar:
    with st.spinner('Acessando dados em tempo real...'):
        df = buscar_dados_crypto(ticker_input)
    
    if df is not None:
        try:
            def extrair_valor(coluna, index=-1):
                val = df[coluna].iloc[index]
                if isinstance(val, (pd.Series, pd.DataFrame)):
                    return float(val.iloc[0])
                return float(val)

            preco_atual = extrair_valor('Close')
            volume_atual = extrair_valor('Volume')
            volume_medio = float(df['Volume'].mean())
            rsi_valor = float(calcular_rsi(df))
            
            # Máximas 90 e 180 dias
            max_180d = float(df['High'].max())
            df_90 = df.iloc[-90:] if len(df) >= 90 else df
            max_90d = float(df_90['High'].max())
            
            # Dashboard Superior
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Preço Atual", f"$ {preco_atual:.4f}")
            with col2:
                st.metric("RSI (14d)", f"{rsi_valor:.1f}")
            with col3:
                vol_label = "Baixo" if volume_atual < volume_medio else "Alto"
                st.metric("Volume", vol_label)

            # --- Seção de Posse e Performance ---
            if ja_possui and preco_analista > 0:
                st.subheader("💼 Minha Posição")
                lucro_prejuizo = ((preco_atual - preco_analista) / preco_analista) * 100
                cor_delta = "normal" if lucro_prejuizo >= 0 else "inverse"
                
                c_pos1, c_pos2 = st.columns(2)
                c_pos1.metric("Preço de Entrada", f"$ {preco_analista:.4f}")
                c_pos2.metric("Resultado Atual", f"{lucro_prejuizo:.2f}%", delta=f"{lucro_prejuizo:.2f}%", delta_color=cor_delta)
                st.divider()

            # --- Radiografia do Mercado ---
            st.subheader("📊 Radiografia do Mercado")
            c1, c2 = st.columns(2)
            c1.info(f"**Máxima 90 dias:** $ {max_90d:.4f}")
            c2.info(f"**Máxima 180 dias
