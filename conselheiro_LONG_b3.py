import streamlit as st
import yfinance as yf
import pandas as pd
import fundamentus
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro B3 Gestor", page_icon="🏢", layout="centered")

# ==========================================
# 2. FUNÇÕES DE BUSCA
# ==========================================

@st.cache_data(ttl=3600)
def buscar_fundamentos_alternativo(ticker):
    """Busca fundamentos no site Fundamentus (Mais estável para B3)"""
    try:
        # Remove o .SA para o fundamentus
        t_limpo = ticker.replace(".SA", "").strip()
        df_f = fundamentus.get_papel(t_limpo)
        
        if df_f.empty:
            return None
            
        return {
            "pl": float(df_f['pl'].iloc[0]) / 100, # Ajuste de escala do fundamentus
            "dy": float(df_f['dy'].iloc[0]) / 100,
            "margem": float(df_f['mrg_liq'].iloc[0]) / 100
        }
    except:
        return None

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker):
    """Busca preços no Yahoo (que continua bom para gráfico)"""
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
    with st.spinner("Buscando Técnica (Yahoo) e Fundamentos (Fundamentus)..."):
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos_alternativo(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            preco_atual = float(atual['fechamento'])
            rsi_valor = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            max_180d = float(df['maxima'].tail(180).max())
            
            # 1. Dash Principal
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            dist_topo = ((max_180d - preco_atual) / max_180d) * 100
            col3.metric("Dist. do Topo", f"{dist_topo:.1f}%")

            # 2. Parecer
            st.subheader("📢 Parecer do Conselheiro")
            if rsi_valor > 70:
                st.warning(f"⚠️ SOBRECOMPRADO: RSI em {rsi_valor:.1f}. Risco de correção.")
            elif preco_atual > m50 and rsi_valor < RSI_MAX_ENTRADA:
                st.success("🟢 COMPRA/APORTE: Tendência de alta e RSI favorável.")
            elif preco_atual < m50:
                st.error("🔴 TENDÊNCIA DE BAIXA: Preço abaixo da média de 50 dias.")
            else:
                st.info("🟡 NEUTRO: Tendência de alta, mas aguarde melhor RSI.")
            
            # 3. Saúde da Empresa (Fundamentalista)
            st.divider()
            st.subheader("🏥 Saúde da Empresa (Fundamentus)")
            if fund:
                f1, f2, f3 = st.columns(3)
                f1.metric("P/L", f"{fund['pl']:.2f}")
                f2.metric("Div. Yield", f"{fund['dy']:.2f}%")
                f3.metric("Margem Líquida", f"{fund['margem']:.2f}%")
            else:
                st.warning("⚠️ Dados do Fundamentus não encontrados para este ticker.")

            # 4. Radiografia e Risco
            st.divider()
            st.subheader("🛡️ Gestão de Risco")
            v_stop = preco_atual * (1 - STOP_LOSS_PCT)
            alvo_sug = ALVO_ANALISTA if ALVO_ANALISTA > 0 else (preco_atual * 1.15)
            g1, g2 = st.columns(2)
            g1.error(f"Stop Loss Sugerido: R$ {v_stop:.2f}")
            g2.success(f"Alvo Estratégico: R$ {alvo_sug:.2f}")

        else:
            st.error("Erro ao carregar dados técnicos. Verifique o ticker.")
