import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 1. Configuração da Página - Carregamento Imediato
st.set_page_config(page_title="Conselheiro B3", page_icon="🏢", layout="centered")

# 2. Funções com Cache (Para não repetir downloads desnecessários)
@st.cache_data(ttl=300)
def obter_dados_limpos(ticker):
    try:
        df = yf.download(ticker, period='150d', interval='1d', progress=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        df = df.reset_index()
        col_f = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df.rename(columns={col_f: 'fechamento', 'Date': 'data'}, inplace=True)
        
        # Indicadores técnicos
        df['ema_9'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (ganho/perda)))
        return df.dropna()
    except:
        return None

# 3. Interface Lateral com Formulário (ISSO DESTRAVA A TELA)
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # O formulário impede que o app tente carregar a cada letra digitada
    with st.form("meu_formulario"):
        SIMBOLO = st.text_input("Ação (ex: PETR4.SA)", value="").upper().strip()
        st.markdown("---")
        STOP_LOSS_PCT = st.number_input("Stop Loss (%)", value=5.0) / 100.0
        TRAILING_STOP_PCT = st.number_input("Trailing Stop (%)", value=10.0) / 100.0
        RSI_MAX = st.number_input("RSI Máx.", value=55)
        
        btn_analisar = st.form_submit_button("🚀 ANALISAR AGORA", use_container_width=True)

# 4. Painel Principal
st.title("🏢 Conselheiro B3")
st.markdown("---")

if btn_analisar:
    if not SIMBOLO:
        st.warning("⚠️ Por favor, digite o código da ação (ex: VALE3.SA).")
    else:
        with st.spinner(f"Buscando dados de {SIMBOLO}..."):
            df = obter_dados_limpos(SIMBOLO)
            
            if df is not None:
                atual = df.iloc[-1]
                anterior = df.iloc[-2]
                preco = float(atual['fechamento'])
                rsi = float(atual['rsi'])
                
                # Lógica de Decisão
                tendencia_alta = preco > float(atual['sma_50'])
                rompeu_ema9 = preco > float(atual['ema_9']) and float(anterior['fechamento']) <= float(anterior['ema_9'])
                
                # Exibição dos Cards
                c1, c2, c3 = st.columns(3)
                c1.metric("Preço", f"R$ {preco:.2f}")
                c2.metric("RSI", f"{rsi:.1f}")
                c3.metric("Média 50", "Acima" if tendencia_alta else "Abaixo")

                if tendencia_alta and rsi < RSI_MAX and rompeu_ema9:
                    st.success("🟢 GATILHO DE COMPRA IDENTIFICADO!")
                elif tendencia_alta and rsi < RSI_MAX:
                    st.info("🟡 EM OBSERVAÇÃO: Aguarde o rompimento da EMA 9.")
                else:
                    st.error("🔴 FORA DO SETUP: Ativo esticado ou em tendência de baixa.")

                # Gestão de Risco
                st.subheader("🛡️ Gestão de Risco")
                v_stop = preco * (1 - STOP_LOSS_PCT)
                v_alvo = preco * (1 + TRAILING_STOP_PCT)
                
                r1, r2 = st.columns(2)
                r1.metric("Stop Loss (Sair)", f"R$ {v_stop:.2f}")
                r2.metric("Ativar Trailing", f"R$ {v_alvo:.2f}")
            else:
                st.error("❌ Não foi possível encontrar esta ação. Verifique se usou o '.SA' no final.")
else:
    st.info("Digite o ticker na esquerda e clique no botão para iniciar.")
