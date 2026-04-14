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
    """Busca indicadores fundamentalistas com tratamento de erro robusto"""
    try:
        acao = yf.Ticker(ticker)
        inf = acao.info
        
        if not inf or len(inf) < 5:
            return {"pl": 0.0, "dy": 0.0, "margem": 0.0}

        # Captura flexível de chaves do Yahoo
        pl = inf.get('forwardPE') or inf.get('trailingPE') or 0.0
        dy = (inf.get('dividendYield') or inf.get('trailingAnnualDividendYield') or 0.0) * 100
        margem = (inf.get('profitMargins') or 0.0) * 100

        return {"pl": float(pl), "dy": float(dy), "margem": float(margem)}
    except:
        return {"pl": 0.0, "dy": 0.0, "margem": 0.0}

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker):
    """Busca preços e calcula RSI/Médias"""
    try:
        df = yf.download(ticker, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data', 'High': 'maxima', 'Volume': 'volume'}, inplace=True)
        
        close_series = df['fechamento']
        if len(close_series.shape) > 1: close_series = close_series.iloc[:, 0]

        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['sma_50'] = close_series.rolling(window=50).mean()
        
        return df.dropna()
    except: return None

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
        # GARANTE QUE AS VARIÁVEIS SEJAM DEFINIDAS
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            preco_atual = float(atual['fechamento'])
            rsi_valor = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            max_180d = float(df['maxima'].tail(180).max())
            
            # 1. Métricas de Topo
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            dist_topo = ((max_180d - preco_atual) / max_180d) * 100
            col3.metric("Dist. do Topo", f"{dist_topo:.1f}%")

            # 2. Parecer
            st.subheader("📢 Parecer do Conselheiro")
            if rsi_valor > 70:
                st.warning("⚠️ SOBRECOMPRADO: Aguarde correção.")
            elif preco_atual > m50 and rsi_valor < RSI_MAX_ENTRADA:
                st.success("🟢 COMPRA/APORTE: Tendência de alta e RSI favorável.")
            elif preco_atual < m50:
                st.error("🔴 TENDÊNCIA DE BAIXA: Evite compras agora.")
            else:
                st.info("🟡 NEUTRO: Aguarde melhor sinal de RSI.")

            # 3. SAÚDE DA EMPRESA (FUNDAMENTALISTA) - BLOCO CORRIGIDO
            st.divider()
            st.subheader("🏥 Saúde da Empresa (Fundamentalista)")
            f1, f2, f3 = st.columns(3)
            
            # Verifica se os dados são válidos antes de exibir
            if fund and (fund['pl'] > 0 or fund['dy'] > 0 or fund['margem'] > 0):
                f1.metric("P/L (Valuation)", f"{fund['pl']:.1f}")
                f2.metric("Dividend Yield", f"{fund['dy']:.2f}%")
                f3.metric("Margem Líquida", f"{fund['margem']:.1f}%")
            else:
                st.info("ℹ️ Indicadores fundamentalistas não disponíveis no Yahoo para este ticker.")

            # 4. Gestão de Risco
            st.divider()
            st.subheader("🛡️ Gestão de Risco")
            v_stop = preco_atual * (1 - STOP_LOSS_PCT)
            st.error(f"Stop Loss Sugerido: R$ {v_stop:.2f}")
            st.success(f"Alvo Estratégico (+15%): R$ {preco_atual * 1.15:.2f}")

        else:
            st.error("Erro ao carregar dados. Verifique o ticker (ex: PETR4.SA).")
