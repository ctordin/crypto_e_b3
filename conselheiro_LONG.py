import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro Crypto Gestor", page_icon="🚀", layout="centered")

# 2. Funções de Busca (Foco em Volume e Preço)
@st.cache_data(ttl=300)
def buscar_dados_crypto(ticker):
    try:
        df = yf.download(ticker, period='100d', interval='1d', progress=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        df = df.reset_index()
        col_f = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df.rename(columns={col_f: 'fechamento', 'Date': 'data', 'Volume': 'volume'}, inplace=True)
        
        # Indicadores Rápidos para Crypto
        df['ema_9'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        # RSI
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (ganho/perda)))
        
        # Média de Volume (Saúde da Rede)
        df['vol_medio'] = df['volume'].rolling(window=20).mean()
        
        return df.dropna()
    except: return None

# 3. Interface Lateral (Gestão de Moedas)
with st.sidebar:
    st.header("⚙️ Portfólio Crypto")
    with st.form("form_crypto"):
        PAR = st.text_input("Par (ex: AVAX-USDT ou BTC-USD)", value="AVAX-USDT").upper().strip()
        
        st.markdown("---")
        JA_COMPREI = st.checkbox("Já possuo esta moeda?")
        MEU_PRECO = st.number_input("Preço de Compra ($)", value=0.0, format="%.4f")
        ALVO_LUCRO = st.number_input("Alvo de Saída ($)", value=0.0, format="%.4f")
        
        st.markdown("---")
        RISCO_PCT = st.number_input("Stop Loss Máximo (%)", value=4.0) / 100.0
        btn_crypto = st.form_submit_button("🚀 CALCULAR ESTRATÉGIA", use_container_width=True)

# 4. Painel Principal
st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.markdown("---")

if btn_crypto:
    with st.spinner(f"Sincronizando Blockchain e Corretora para {PAR}..."):
        df = buscar_dados_crypto(PAR)
        
        if df is not None:
            atual = df.iloc[-1]
            anterior = df.iloc[-2]
            preco_atual = float(atual['fechamento'])
            rsi = float(atual['rsi'])
            vol_atual = float(atual['volume'])
            vol_m = float(atual['vol_medio'])
            
            # BLOCO A: MINHA CARTEIRA (AVAX Exemplo)
            if JA_COMPREI and MEU_PRECO > 0:
                lucro_abs = preco_atual - MEU_PRECO
                lucro_pct = (lucro_abs / MEU_PRECO) * 100
                
                st.subheader("💰 Status da Moeda")
                m1, m2, m3 = st.columns(3)
                m1.metric("Preço Médio", f"$ {MEU_PRECO:.4f}")
                m2.metric("Lucro Atual", f"$ {lucro_abs:.4f}", f"{lucro_pct:.2f}%")
                
                if ALVO_LUCRO > 0:
                    falta = ((ALVO_LUCRO / preco_atual) - 1) * 100
                    m3.metric("Falta para Alvo", f"{falta:.1f}%")
                
                if lucro_pct > 10:
                    st.balloons()
                    st.success(f"Ótimo lucro! Considere realizar 25% da posição e subir o Stop.")
                st.markdown("---")

            # BLOCO B: MOMENTO TÉCNICO (QUANTITATIVO)
            st.subheader("📊 Radiografia do Mercado")
            tend_alta = preco_atual > float(atual['sma_50'])
            vol_saudavel = vol_atual > vol_m * 0.8 # Pelo menos 80% da média
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Preço Atual", f"$ {preco_atual:.4f}")
            c2.metric("RSI (Índice Força)", f"{rsi:.1f}")
            c3.metric("Volume", "Saudável" if vol_saudavel else "Baixo")

            if rsi > 70:
                st.warning("⚠️ SOBRECOMPRA: O mercado está eufórico. Risco alto de correção.")
            elif tend_alta and rsi < 55:
                st.success("🟢 COMPRA/APORTE: Moeda em tendência com preço descontado.")
            else:
                st.info("🟡 NEUTRO: Aguarde uma definição de volume ou recuo no RSI.")

            # BLOCO C: PROTEÇÃO DE CAPITAL
            st.subheader("🛡️ Gestão de Saída")
            v_stop = preco_atual * (1 - RISCO_PCT)
            
            r1, r2 = st.columns(2)
            # Se o preço de compra existe, mostra se o stop é com lucro ou prejuízo
            delta_stop = ""
            if JA_COMPREI and MEU_PRECO > 0:
                status_s = "Lucro" if v_stop > MEU_PRECO else "Prejuízo"
                delta_stop = f"({status_s})"
                
            r1.metric(f"Stop Loss {delta_stop}", f"$ {v_stop:.4f}", help="Coloque esta ordem Stop-Market na corretora.")
            
            alvo_sugestao = ALVO_LUCRO if ALVO_LUCRO > 0 else (preco_atual * 1.20)
            r2.metric("Alvo Sugerido", f"$ {alvo_sugestao:.4f}", "+20%" if ALVO_LUCRO == 0 else "Manual")
            
        else:
            st.error("Erro ao buscar par de moedas. Tente AVAX-USD ou BTC-USDT.")
else:
    st.info("Informe seus dados de compra na esquerda para gerenciar sua posição.")
