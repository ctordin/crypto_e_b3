import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro B3 Gestor", page_icon="🏢", layout="centered")

# ==========================================
# 2. FUNÇÕES DE BUSCA (Devem vir ANTES do uso)
# ==========================================

@st.cache_data(ttl=3600)
def buscar_fundamentos(ticker):
    """Busca dados de saúde financeira da empresa"""
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
    """Busca preços e calcula RSI/Médias (Blindado para SMTO3 e B3)"""
    try:
        df = yf.download(ticker, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: 
            return None
        
        # Ajuste para colunas MultiIndex (comum na B3)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data', 'High': 'maxima', 'Volume': 'volume'}, inplace=True)
        
        # Garante que pegamos a coluna correta mesmo se houver duplicidade (caso SMTO3)
        close_series = df['fechamento']
        if len(close_series.shape) > 1:
            close_series = close_series.iloc[:, 0]

        # RSI
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Médias
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
        RSI_MAX = st.number_input("RSI Máx. (Entrada)", value=55)
        btn_analisar = st.form_submit_button("🚀 ANALISAR AGORA", use_container_width=True)

# ==========================================
# 4. PAINEL PRINCIPAL
# ==========================================
st.title("🏢 Conselheiro B3: Gestor de Posição")
st.divider()

if btn_analisar:
    with st.spinner("Sincronizando dados..."):
        # Agora as funções já foram definidas acima, o erro sumirá
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            preco_atual = float(atual['fechamento'])
            rsi_valor = float(atual['rsi'])
            
            # Máximas 90/180
            max_180d = float(df['maxima'].tail(180).max())
            max_90d = float(df['maxima'].tail(90).max())

            # Métricas Superiores
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            col3.metric("Máxima 180d", f"R$ {max_180d:.2f}")

            if POSSUO_ACAO and PRECO_COMPRA > 0:
                st.subheader("💰 Minha Posição")
                lucro_pct = ((preco_atual - PRECO_COMPRA) / PRECO_COMPRA) * 100
                st.metric("Resultado", f"{lucro_pct:.2f}%", delta=f"{lucro_pct:.2f}%")
                st.divider()

            # Saúde Financeira (Fundamentos)
            if fund:
                st.subheader("📊 Saúde da Empresa")
                f1, f2, f3 = st.columns(3)
                f1.metric("P/L", f"{fund['pl']:.1f}")
                f2.metric("Div. Yield", f"{fund['dy']:.1f}%")
                f3.metric("Margem", f"{fund['margem']:.1f}%")
                st.divider()

            # Gestão de Risco
            st.subheader("🛡️ Gestão de Risco")
            v_stop = preco_atual * (1 - STOP_LOSS_PCT)
            st.error(f"Stop Loss Sugerido: R$ {v_stop:.2f}")
            st.success(f"Alvo Sugerido (+15%): R$ {preco_atual * 1.15:.2f}")

        else:
            st.error("Erro ao carregar dados. Verifique o ticker (ex: PETR4.SA).")
