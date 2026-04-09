import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA WEB
# ==========================================
st.set_page_config(page_title="Conselheiro B3 Quantamental", page_icon="🏢", layout="centered")

# ==========================================
# 2. BARRA LATERAL (MENU INTERATIVO)
# ==========================================
st.sidebar.header("⚙️ Parâmetros da Ação")
SIMBOLO = st.sidebar.text_input("Ação (ex: VALE3.SA, ITUB4.SA)", value="VALE3.SA").upper().strip()

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Gestão de Risco (Gabarito)")
STOP_LOSS_PCT = st.sidebar.number_input("Stop Loss (%)", min_value=1.0, max_value=15.0, value=5.0, step=1.0) / 100.0
TRAILING_STOP_PCT = st.sidebar.number_input("Trailing Stop (%)", min_value=1.0, max_value=30.0, value=10.0, step=1.0) / 100.0
RSI_MAX_ENTRADA = st.sidebar.number_input("RSI Máx. (Promoção)", min_value=30, max_value=80, value=55, step=1)

# ==========================================
# 3. MOTOR DE DADOS (FUNDAMENTOS + GRÁFICO)
# ==========================================
@st.cache_data(ttl=3600)
def obter_fundamentos(ticker):
    try:
        acao = yf.Ticker(ticker)
        info = acao.info
        dados = {
            "pl": info.get('forwardPE') or info.get('trailingPE') or 0,
            "dy": (info.get('dividendYield') or 0) * 100,
            "margem": (info.get('profitMargins') or 0) * 100,
            "saudavel": (info.get('profitMargins') or 0) > 0.05 and (info.get('forwardPE') or 100) < 25
        }
        return dados
    except:
        return None

@st.cache_data(ttl=300) 
def obter_dados_graficos(ticker):
    try:
        df = yf.download(ticker, period='150d', interval='1d', progress=False)
        if df.empty or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        df = df.reset_index()
        fechamento = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df.rename(columns={fechamento: 'fechamento', 'Date': 'data'}, inplace=True)
        
        df['ema_9'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (ganho/perda)))
        return df.dropna()
    except:
        return None

# ==========================================
# 4. INTERFACE PRINCIPAL
# ==========================================
st.title("🏢 Conselheiro B3 Quantamental")
st.markdown("Análise final de saúde financeira e pontos de entrada.")
st.markdown("---")

if st.sidebar.button("Analisar Ação", type="primary", use_container_width=True):
    fund = obter_fundamentos(SIMBOLO)
    df = obter_dados_graficos(SIMBOLO)

    if fund and df is not None:
        atual = df.iloc[-1]
        anterior = df.iloc[-2]
        preco = float(atual['fechamento'])

        # Bloco Fundamentalista
        st.subheader("📊 Saúde da Empresa (Fundamentos)")
        c1, c2, c3 = st.columns(3)
        c1.metric("P/L (Preço/Lucro)", f"{fund['pl']:.1f}")
        c2.metric("Dividend Yield", f"{fund['dy']:.1f}%")
        c3.metric("Margem Líquida", f"{fund['margem']:.1f}%")

        if not fund['saudavel']:
            st.warning("⚠️ **Aviso:** Esta empresa possui fundamentos fora do padrão ideal (Margem baixa ou P/L muito alto).")
        
        st.markdown("---")

        # Lógica Técnica
        tendencia_alta = preco > float(atual['sma_50'])
        em_promocao = float(atual['rsi']) < RSI_MAX_ENTRADA
        rompeu_ema9 = preco > float(atual['ema_9']) and float(anterior['fechamento']) <= float(anterior['ema_9'])

        if tendencia_alta and em_promocao and rompeu_ema9:
            st.success("🚀 **GATILHO DE COMPRA ACIONADO!**\n\nAtivo em tendência de alta, com desconto e retomada de força.")
            recomendacao = "COMPRA"
        elif tendencia_alta and em_promocao:
            st.info("👀 **PREPARAR COMPRA**\n\nAtivo barato, mas ainda sem sinal de virada no preço. Aguarde romper a EMA 9.")
            recomendacao = "ESPERAR"
        else:
            st.error("❌ **NÃO COMPRAR**\n\nO ativo está esticado ou em tendência de baixa.")
            recomendacao = "FORA"

        # Radiografia Técnica
        st.subheader("📈 Radiografia Técnica")
        col1, col2, col3 = st.columns(3)
        col1.metric("Preço Atual", f"R$ {preco:.2f}")
        col2.metric("Tendência (50)", "Alta" if tendencia_alta else "Baixa")
        col3.metric(f"RSI (Max {RSI_MAX_ENTRADA})", f"{atual['rsi']:.1f}")

        # Gestão de Risco
        if recomendacao != "FORA":
            st.markdown("### 🛡️ Gestão de Risco Estrita")
            v_stop = preco * (1 - STOP_LOSS_PCT)
            v_alvo = preco * (1 + TRAILING_STOP_PCT)
            col4, col5 = st.columns(2)
            col4.metric(f"Stop Loss (-{STOP_LOSS_PCT*100:.0f}%)", f"R$ {v_stop:.2f}")
            col5.metric(f"Ativar Trailing (+{TRAILING_STOP_PCT*100:.0f}%)", f"R$ {v_alvo:.2f}")
    else:
        st.error("Não foi possível carregar os dados. Verifique se o ticker (ex: VALE3.SA) está correto.")
else:
    st.write("👈 Configure os parâmetros e clique em **Analisar Ação**.")
