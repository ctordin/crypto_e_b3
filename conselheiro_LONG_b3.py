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
def buscar_fundamentos_alternativo(ticker_br):
    """Busca no Fundamentus (sem .SA)"""
    try:
        # Limpa o ticker para o padrão Fundamentus (ex: VALE3)
        t_limpo = ticker_br.replace(".SA", "").strip().upper()
        df_f = fundamentus.get_papel(t_limpo)
        
        if df_f is None or df_f.empty:
            return None
            
        return {
            "pl": float(df_f['pl'].iloc[0]),
            "dy": float(df_f['dy'].iloc[0]),
            "margem": float(df_f['mrg_liq'].iloc[0])
        }
    except:
        return None

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker_yf):
    """Busca preços no Yahoo (sempre com .SA)"""
    try:
        # Garante o .SA para o Yahoo Finance
        if not ticker_yf.endswith(".SA"):
            ticker_yf = f"{ticker_yf}.SA"
            
        df = yf.download(ticker_yf, period='250d', interval='1d', progress=False, auto_adjust=True)
        
        if df is None or df.empty: 
            return None
            
        # Limpeza de colunas (essencial para SMTO3 e ativos B3)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data', 'High': 'maxima'}, inplace=True)
        
        # Pega a coluna de fechamento (mesmo se vier duplicada)
        close_series = df['fechamento']
        if len(close_series.shape) > 1:
            close_series = close_series.iloc[:, 0]

        # RSI (14)
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Média 50
        df['sma_50'] = close_series.rolling(window=50).mean()
        
        return df.dropna()
    except Exception as e:
        st.error(f"Erro interno: {e}")
        return None

# ==========================================
# 3. INTERFACE LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Parâmetros")
    with st.form("form_gestor"):
        # Se você digitar SMTO3 ou SMTO3.SA, o código vai tratar
        SIMBOLO_RAW = st.text_input("Ação (ex: VALE3)", value="ALOS3").upper().strip()
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
    with st.spinner("Conectando aos servidores B3..."):
        # Busca nas duas fontes
        df = buscar_dados_mercado(SIMBOLO_RAW)
        fund = buscar_fundamentos_alternativo(SIMBOLO_RAW)
        
        if df is not None:
            atual = df.iloc[-1]
            # Garante que o preço seja tratado como float simples
            p_fechamento = atual['fechamento']
            if isinstance(p_fechamento, pd.Series): p_fechamento = p_fechamento.iloc[0]
            
            preco_atual = float(p_fechamento)
            rsi_valor = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            max_180d = float(df['maxima'].tail(180).max())

            # 1. Dashboard Principal
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            dist_topo = ((max_180d - preco_atual) / max_180d) * 100
            col3.metric("Dist. do Topo", f"{dist_topo:.1f}%")

            # 2. Parecer Técnico
            st.subheader("📢 Parecer do Conselheiro")
            if rsi_valor > 70:
                st.warning(f"⚠️ SOBRECOMPRADO: RSI em {rsi_valor:.1f}. Aguarde correção.")
            elif preco_atual > m50 and rsi_valor < RSI_MAX_ENTRADA:
                st.success("🟢 COMPRA/APORTE: Tendência de alta e RSI em zona de desconto.")
            elif preco_atual < m50:
                st.error("🔴 TENDÊNCIA DE BAIXA: Preço abaixo da média de 50 dias.")
            else:
                st.info("🟡 NEUTRO: Tendência de alta, mas aguarde melhor RSI.")
            
            # 3. Saúde da Empresa (Fundamentus)
            st.divider()
            st.subheader("🏥 Saúde da Empresa (Fundamentus)")
            if fund:
                f1, f2, f3 = st.columns(3)
                f1.metric("P/L", f"{fund['pl']:.2f}")
                f2.metric("Div. Yield", f"{fund['dy']:.2f}%")
                f3.metric("Margem Líquida", f"{fund['margem']:.2f}%")
            else:
                st.info("ℹ️ Dados fundamentalistas indisponíveis para este ticker no Fundamentus.")

            # 4. Gestão de Risco
            st.divider()
            st.subheader("🛡️ Gestão de Risco")
            v_stop = preco_atual * (1 - STOP_LOSS_PCT)
            alvo_sug = ALVO_ANALISTA if ALVO_ANALISTA > 0 else (preco_atual * 1.15)
            g1, g2 = st.columns(2)
            g1.error(f"Stop Loss Sugerido: R$ {v_stop:.2f}")
            g2.success(f"Alvo Estratégico: R$ {alvo_sug:.2f}")

        else:
            st.error(f"❌ Erro ao carregar dados técnicos do Yahoo para '{SIMBOLO_RAW}'. Verifique a conexão.")
