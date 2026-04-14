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
def buscar_fundamentos(ticker_raw):
    """Busca fundamentos com tratamento de erro em cascata"""
    t_yf = ticker_raw if ".SA" in ticker_raw.upper() else f"{ticker_raw.upper()}.SA"
    try:
        acao = yf.Ticker(t_yf)
        # O método .info é o que mais trava, então buscamos chaves específicas
        inf = acao.info
        
        # P/L (Preço/Lucro)
        pl = inf.get('forwardPE') or inf.get('trailingPE') or 0.0
        
        # DY (Dividend Yield)
        dy = (inf.get('dividendYield') or inf.get('trailingAnnualDividendYield') or 0.0) * 100
        
        # Margem Líquida
        margem = (inf.get('profitMargins') or 0.0) * 100

        # Se vier tudo zerado, retornamos None para o aviso aparecer
        if pl == 0 and dy == 0 and margem == 0:
            return None
            
        return {"pl": float(pl), "dy": float(dy), "margem": float(margem)}
    except:
        return None

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker_raw):
    """Busca preços e indicadores técnicos"""
    t_yf = ticker_raw if ".SA" in ticker_raw.upper() else f"{ticker_raw.upper()}.SA"
    try:
        df = yf.download(t_yf, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data', 'High': 'maxima'}, inplace=True)
        
        close_series = df['fechamento']
        if len(close_series.shape) > 1: close_series = close_series.iloc[:, 0]

        # RSI (14)
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
st.sidebar.header("⚙️ Parâmetros")
with st.sidebar.form("form_gestor"):
    SIMBOLO = st.text_input("Ação (Ex: ALOS3)", value="ALOS3").strip()
    POSSUO = st.checkbox("Já possuo?")
    COMPRA = st.number_input("Preço Compra (R$)", value=0.0)
    STOP_PCT = st.number_input("Stop Loss %", value=5.0) / 100
    RSI_MAX = st.number_input("RSI Máx Entrada", value=55)
    btn = st.form_submit_button("🚀 ANALISAR AGORA")

# ==========================================
# 4. PAINEL PRINCIPAL
# ==========================================
st.title("🏢 Conselheiro B3: Gestor de Posição")
st.divider()

if btn:
    with st.spinner("Sincronizando com a B3..."):
        df_tecnico = buscar_dados_mercado(SIMBOLO)
        dados_fund = buscar_fundamentos(SIMBOLO)
        
        if df_tecnico is not None:
            # Dados técnicos atuais
            atual = df_tecnico.iloc[-1]
            p_fech = atual['fechamento']
            if isinstance(p_fech, pd.Series): p_fech = p_fech.iloc[0]
            
            p_atual = float(p_fech)
            rsi = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            max180 = float(df_tecnico['maxima'].tail(180).max())

            # 1. Dashboard Superior
            c1, c2, c3 = st.columns(3)
            c1.metric("Preço Atual", f"R$ {p_atual:.2f}")
            c2.metric("RSI (14d)", f"{rsi:.1f}")
            c3.metric("Máxima 180d", f"R$ {max180:.2f}")

            # 2. Parecer
            st.subheader("📢 Parecer do Conselheiro")
            if rsi > 70: st.warning(f"⚠️ SOBRECOMPRADO (RSI: {rsi:.1f}). Risco de correção alto.")
            elif p_atual > m50 and rsi < RSI_MAX: st.success("🟢 COMPRA/APORTE: Tendência de alta e RSI em zona de desconto.")
            elif p_atual < m50: st.error("🔴 TENDÊNCIA DE BAIXA: Preço abaixo da média macro de 50 dias.")
            else: st.info("🟡 NEUTRO: Tendência de alta, mas aguarde melhor RSI para entrar.")

            # 3. Saúde Financeira
            st.divider()
            st.subheader("🏥 Saúde da Empresa (Fundamentalista)")
            if dados_fund:
                f1, f2, f3 = st.columns(3)
                f1.metric("P/L", f"{dados_fund['pl']:.1f}" if dados_fund['pl'] > 0 else "N/A")
                f2.metric("Div. Yield", f"{dados_fund['dy']:.2f}%" if dados_fund['dy'] > 0 else "N/A")
                f3.metric("Margem Líquida", f"{dados_fund['margem']:.1f}%" if dados_fund['margem'] > 0 else "N/A")
            else:
                st.info("ℹ️ Indicadores fundamentalistas temporariamente indisponíveis no servidor.")

            # 4. Gestão de Risco
            st.divider()
            st.subheader("🛡️ Gestão de Risco")
            v_stop = p_atual * (1 - STOP_PCT)
            st.error(f"Stop Loss Sugerido: R$ {v_stop:.2f}")
            st.success(f"Alvo Estratégico (+15%): R$ {p_atual * 1.15:.2f}")
        else:
            st.error("Erro ao carregar dados técnicos. Verifique se o ticker está correto (ex: VALE3).")
