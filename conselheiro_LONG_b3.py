import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro B3 Gestor", page_icon="🏢", layout="centered")

# ==========================================
# 2. FUNÇÕES DE BUSCA (Devem vir primeiro!)
# ==========================================

@st.cache_data(ttl=3600)
def buscar_fundamentos(ticker):
    """Busca fundamentos com proteção total contra bloqueio (Silent Fail)"""
    try:
        acao = yf.Ticker(ticker)
        # Tenta pegar apenas o Dividend Yield que é o mais importante e falha menos
        divs = acao.dividends
        dy = 0.0
        if not divs.empty:
            ultimos_12m = divs[divs.index > (pd.Timestamp.now() - pd.Timedelta(days=365))]
            dy = (ultimos_12m.sum() / acao.history(period="1d")['Close'].iloc[-1]) * 100
            
        inf = acao.info
        return {
            "pl": inf.get('forwardPE') or inf.get('trailingPE') or 0.0,
            "dy": dy if dy > 0 else (inf.get('dividendYield', 0) * 100),
            "margem": (inf.get('profitMargins') or 0.0) * 100
        }
    except:
        return None # Retorna None para o app saber que o Yahoo bloqueou

# --- No bloco de exibição (dentro do if btn_analisar) ---
if fund:
    st.subheader("🏥 Saúde da Empresa (Fundamentalista)")
    f1, f2, f3 = st.columns(3)
    f1.metric("P/L", f"{fund['pl']:.1f}" if fund['pl'] > 0 else "N/A")
    f2.metric("Div. Yield", f"{fund['dy']:.2f}%" if fund['dy'] > 0 else "N/A")
    f3.metric("Margem", f"{fund['margem']:.1f}%" if fund['margem'] > 0 else "N/A")
else:
    st.info("ℹ️ Dados fundamentalistas (P/L, DY) temporariamente indisponíveis no Yahoo. Foco na Análise Técnica abaixo.")
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
# 4. PAINEL PRINCIPAL (A execução vem aqui)
# ==========================================
st.title("🏢 Conselheiro B3: Gestor de Posição")
st.divider()

if btn_analisar:
    with st.spinner("Sincronizando dados..."):
        # Agora as funções já foram carregadas no topo do arquivo
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            preco_atual = float(atual['fechamento'])
            rsi_valor = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            max_180d = float(df['maxima'].tail(180).max())
            max_90d = float(df['maxima'].tail(90).max())

            # DASHBOARD PRINCIPAL
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            dist_topo = ((max_180d - preco_atual) / max_180d) * 100
            col3.metric("Dist. do Topo", f"{dist_topo:.1f}%")

            # PARECER TÉCNICO
            st.subheader("📢 Parecer do Conselheiro")
            tend_alta = preco_atual > m50
            if rsi_valor > 70:
                st.warning(f"⚠️ SOBRECOMPRADO: RSI em {rsi_valor:.1f}. Aguarde correção.")
            elif tend_alta and rsi_valor < RSI_MAX_ENTRADA:
                st.success("🟢 COMPRA/APORTE: Tendência de alta e RSI em zona de desconto.")
            elif not tend_alta:
                st.error("🔴 TENDÊNCIA DE BAIXA: Preço abaixo da média de 50 dias.")
            else:
                st.info("🟡 NEUTRO: Tendência de alta, mas aguarde melhor RSI.")
            st.divider()

            # INDICADORES FUNDAMENTALISTAS
            st.subheader("🏥 Saúde da Empresa (Fundamentalista)")
            f1, f2, f3 = st.columns(3)
            
            val_pl = f"{fund['pl']:.1f}" if fund['pl'] > 0 else "N/A"
            f1.metric("P/L (Valuation)", val_pl)
            
            val_dy = f"{fund['dy']:.2f}%" if fund['dy'] > 0 else "N/A"
            f2.metric("Dividend Yield", val_dy)
            
            val_mg = f"{fund['margem']:.1f}%" if fund['margem'] > 0 else "N/A"
            f3.metric("Margem Líquida", val_mg)
            st.divider()

            # RADIOGRAFIA DE MERCADO
            st.subheader("📊 Radiografia do Mercado")
            r1, r2 = st.columns(2)
            r1.info(f"**Máxima 90 dias:** R$ {max_90d:.2f}")
            r2.info(f"**Máxima 180 dias:** R$ {max_180d:.2f}")

            # GESTÃO DE RISCO
            st.divider()
            st.subheader("🛡️ Gestão de Risco")
            v_stop = preco_atual * (1 - STOP_LOSS_PCT)
            alvo_sug = ALVO_ANALISTA if ALVO_ANALISTA > 0 else (preco_atual * 1.15)
            
            g1, g2 = st.columns(2)
            g1.error(f"Stop Loss Sugerido: R$ {v_stop:.2f}")
            g2.success(f"Alvo Estratégico: R$ {alvo_sug:.2f}")

        else:
            st.error("Erro ao carregar dados. Verifique o ticker (ex: PETR4.SA).")
