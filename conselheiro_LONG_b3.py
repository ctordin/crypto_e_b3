import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro B3 Gestor", page_icon="🏢", layout="centered")

# ==========================================
# 2. FUNÇÕES DE BUSCA
# ==========================================

@st.cache_data(ttl=3600)
def buscar_fundamentos(ticker):
    try:
        acao = yf.Ticker(ticker)
        inf = acao.info
        if not inf or len(inf) < 5: 
            return None
        return {
            "pl": inf.get('forwardPE') or inf.get('trailingPE') or 0,
            "dy": (inf.get('dividendYield') or 0) * 100,
            "margem": (inf.get('profitMargins') or 0) * 100
        }
    except:
        return None

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker):
    try:
        df = yf.download(ticker, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: 
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data', 'High': 'maxima', 'Volume': 'volume'}, inplace=True)
        
        close_series = df['fechamento']
        if len(close_series.shape) > 1:
            close_series = close_series.iloc[:, 0]

        # RSI
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Média 50
        df['sma_50'] = close_series.rolling(window=50).mean()
        
        return df.dropna()
    except:
        return None

# ==========================================
# 3. INTERFACE LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Parâmetros")
    with st.form("form_gestor"):
        SIMBOLO = st.text_input("Ação (ex: VALE3.SA)", value="ALOS3.SA").upper().strip()
        st.markdown("---")
        POSSUO_ACAO = st.checkbox("Já possuo esta ação?")
        PRECO_COMPRA = st.number_input("Meu Preço de Compra (R$)", value=0.0, step=0.01)
        ALVO_ANALISTA = st.number_input("Alvo do Analista (R$)", value=0.0, step=0.01)
        st.markdown("---")
        STOP_LOSS_PCT = st.number_input("Stop Loss desejado (%)", value=5.0) / 100.0
        RSI_MAX_ENTRADA = st.number_input("RSI Máx. (Entrada)", value=55)
        btn_analisar = st.form_submit_button("🚀 ANALISAR AGORA", use_container_width=True)

# ==========================================
# 4. PAINEL PRINCIPAL
# ==========================================
st.title("🏢 Conselheiro B3: Gestor de Posição")
st.divider()

if btn_analisar:
    with st.spinner("Sincronizando dados..."):
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            preco_atual = float(atual['fechamento'])
            rsi_valor = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            
            # CÁLCULO DE MÁXIMAS
            max_180d = float(df['maxima'].tail(180).max())
            max_90d = float(df['maxima'].tail(90).max())

            # Métricas Superiores
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            dist_topo = ((max_180d - preco_atual) / max_180d) * 100
            col3.metric("Dist. do Topo", f"{dist_topo:.1f}%")

            if POSSUO_ACAO and PRECO_COMPRA > 0:
                st.subheader("💰 Minha Posição")
                lucro_pct = ((preco_atual - PRECO_COMPRA) / PRECO_COMPRA) * 100
                st.metric("Resultado Atual", f"{lucro_pct:.2f}%", delta=f"{lucro_pct:.2f}%")
                st.divider()

            # --- PARECER DO CONSELHEIRO (RESTAURADO) ---
            st.subheader("📢 Parecer do Conselheiro")
            tend_alta = preco_atual > m50
            
            if rsi_valor > 70:
                st.warning(f"⚠️ SOBRECOMPRADO: RSI em {
