import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conselheiro Crypto", layout="wide")

def buscar_dados_crypto(ticker, dias=180):
    try:
        # Busca dados e força o arredondamento/ajuste automático
        data = yf.download(ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True)
        
        if data.empty:
            return None
        
        # TRATAMENTO CRUCIAL: Se as colunas vierem duplicadas (MultiIndex), achata para nível único
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        return data
    except Exception:
        return None

def calcular_rsi(data, window=14):
    # Garante que Close seja uma série simples (1D)
    close = data['Close'].iloc[:, 0] if len(data['Close'].shape) > 1 else data['Close']
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    # Evita divisão por zero
    rs = gain / loss.replace(0, 0.001)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Portfólio Crypto")
ticker_input = st.sidebar.text_input("Par (ex: AVAX-USD)", "AVAX-USD")
stop_loss_max = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_calcular = st.sidebar.button("🚀 CALCULAR ESTRATÉGIA")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_calcular:
    with st.spinner('Acessando mercado...'):
        df = buscar_dados_crypto(ticker_input)
    
    if df is not None:
        try:
            # Extração garantindo valor escalar (float puro)
            # Usamos .iloc[-1] e garantimos que pegamos apenas o primeiro valor caso haja duplicidade
            def extrair_valor(coluna, index=-1):
                val = df[coluna].iloc[index]
                if isinstance(val, (pd.Series, pd.DataFrame)):
                    return float(val.iloc[0])
                return float(val)

            preco_atual = extrair_valor('Close')
            volume_atual = extrair_valor('Volume')
            volume_medio = float(df['Volume'].mean())
            rsi_valor = float(calcular_rsi(df))
            
            # Máximas 
            max_180d = float(df['High'].max())
            # Garante que tenta pegar 90 dias ou o máximo disponível
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

            # --- Radiografia do Mercado ---
            st.subheader("📊 Radiografia do Mercado")
            
            c1, c2 = st.columns(2)
            c1.info(f"**Máxima 90 dias:** $ {max_90d:.4f}")
            c2.info(f"**Máxima 180 dias:** $ {max_180d:.4f}")

            # Lógica de Status
            if rsi_valor < 35:
                st.success("🟢 OPORTUNIDADE: Ativo sobrevendido.")
            elif rsi_valor > 65:
                st.warning("🔴 ALERTA: Ativo sobrecomprado.")
            else:
                st.info("🟡 NEUTRO: Aguarde definição de volume.")

            # --- Gestão de Saída ---
            st.subheader("🛡️ Gestão de Saída")
            
            valor_stop = preco_atual * (1 - (stop_loss_max / 100))
            alvo_sugerido = preco_atual * 1.20

            col_s1, col_s2 = st.columns(2)
            col_s1.error(f"Stop Loss Sugerido: $ {valor_stop:.4f}")
            col_s2.success(f"Alvo Sugerido (+20%): $ {alvo_sugerido:.4f}")
            
            distancia_topo = ((max_180d - preco_atual) / max_180d) * 100
            st.write(f"---")
            st.write(f"**Análise de Ciclo:** O preço atual está a **{distancia_topo:.1f}%** abaixo da máxima de 180 dias.")

        except Exception as e:
            st.error(f"Erro técnico no processamento: {e}")
    else:
        st.error("Erro: Ticker não encontrado ou API fora do ar.")
else:
    st.write("Aguardando comando...")
