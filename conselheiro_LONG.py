import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro Advisor", layout="wide")

def buscar_dados(ticker, dias=180):
    ticker = ticker.upper().strip()
    
    # Tratamento específico para o ZBT
    if ticker == "ZBT" or ticker == "ZBT1":
        ticker = "ZBT1-USD"
    
    # Regra geral para outros ativos
    elif "-" not in ticker and "." not in ticker:
        if any(char.isdigit() for char in ticker):
            ticker = f"{ticker}.SA"
        else:
            ticker = f"{ticker}-USD"
            
    try:
        # Adicionado o parâmetro 'threads=False' para maior estabilidade no Streamlit
        data = yf.download(ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True, threads=False)
        if data.empty:
            return None, ticker
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data, ticker
    except Exception:
        return None, ticker

def calcular_rsi(data, window=14):
    close = data['Close'].iloc[:, 0] if len(data['Close'].shape) > 1 else data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 0.001)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Configurações de Análise")
ticker_input = st.sidebar.text_input("Ativo (ex: ZBT, AVAX ou PETR4)", "ZBT")

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?", value=False)
preco_analista = st.sidebar.number_input("Meu Preço de Compra ($/R$)", format="%.4f", value=0.0)
stop_loss_max = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_confirmar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Pro: B3 & Crypto")
st.divider()

if btn_confirmar:
    with st.spinner('Acessando dados em tempo real...'):
        df, ticker_final = buscar_dados(ticker_input)
    
    if df is not None:
        try:
            def extrair_valor(coluna, index=-1):
                val = df[coluna].iloc[index]
                return float(val.iloc[0]) if isinstance(val, (pd.Series, pd.DataFrame)) else float(val)

            preco_atual = extrair_valor('Close')
            volume_atual = extrair_valor('Volume')
            volume_medio = float(df['Volume'].mean())
            rsi_valor = float(calcular_rsi(df))
            
            # --- CÁLCULO SMA 50 (Solicitado pelo usuário) ---
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            sma50_atual = float(df['SMA50'].iloc[-1])
            
            # Máximas 180 dias
            max_180d = float(df['High'].max())
            
            # Dashboard Superior
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Preço Atual", f"$ {preco_atual:.4f}" if "-USD" in ticker_final else f"R$ {preco_atual:.2f}")
            with col2:
                st.metric("RSI (14d)", f"{rsi_valor:.1f}")
            with col3:
                st.metric("SMA 50", f"{sma50_atual:.4f}")
            with col4:
                vol_label = "Baixo" if volume_atual < volume_medio else "Alto"
                st.metric("Volume", vol_label)

            # --- Análise de SMA 50 ---
            if preco_atual > sma50_atual:
                st.success(f"📈 **Tendência de Alta:** O preço está acima da SMA 50 ({sma50_atual:.4f}).")
            else:
                st.error(f"📉 **Tendência de Baixa:** O preço está abaixo da SMA 50 ({sma50_atual:.4f}).")

            # --- Seção de Posse ---
            if ja_possui and preco_analista > 0:
                st.subheader("💼 Minha Posição")
                lucro_prejuizo = ((preco_atual - preco_analista) / preco_analista) * 100
                cor_delta = "normal" if lucro_prejuizo >= 0 else "inverse"
                c_pos1, c_pos2 = st.columns(2)
                c_pos1.metric("Preço de Entrada", f"{preco_analista:.4f}")
                c_pos2.metric("Resultado Atual", f"{lucro_prejuizo:.2f}%", delta=f"{lucro_prejuizo:.2f}%", delta_color=cor_delta)
                st.divider()

            # --- Radiografia do Mercado ---
            st.subheader("📊 Radiografia e RSI")
            if rsi_valor < 35:
                st.success("🟢 OPORTUNIDADE: Ativo sobrevendido (RSI Baixo).")
            elif rsi_valor > 65:
                st.warning("🔴 ALERTA: Ativo sobrecomprado (RSI Alto).")
            else:
                st.info("🟡 NEUTRO: RSI em zona de equilíbrio.")

            # --- Gestão de Saída ---
            st.subheader("🛡️ Gestão de Risco")
            valor_stop = preco_atual * (1 - (stop_loss_max / 100))
            alvo_sugerido = preco_atual * 1.20
            col_s1, col_s2 = st.columns(2)
            col_s1.error(f"Stop Loss Sugerido: {valor_stop:.4f}")
            col_s2.success(f"Alvo Sugerido (+20%): {alvo_sugerido:.4f}")
            
            st.caption(f"Analisando ticker oficial: {ticker_final}")

        except Exception as e:
            st.error(f"Erro ao processar valores: {e}")
    else:
        st.error(f"Erro: Não foi possível encontrar dados para '{ticker_input}'.")
else:
    st.info("Insira um ativo (ex: ZBT ou PETR4) e clique em atualizar.")
