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
def buscar_fundamentos_alternativo(ticker_raw):
    """Tenta buscar no Fundamentus e, se falhar, tenta Yahoo (Plano C)"""
    # Limpa ticker para o Fundamentus (apenas letras e números)
    t_fund = ticker_raw.split('.')[0].strip().upper()
    
    try:
        # Tenta Fundamentus
        df_f = fundamentus.get_papel(t_fund)
        if df_f is not None and not df_f.empty:
            return {
                "pl": float(df_f['pl'].iloc[0]) / 100,
                "dy": float(df_f['dy'].iloc[0]) / 100,
                "margem": float(df_f['mrg_liq'].iloc[0]) / 100,
                "fonte": "Fundamentus"
            }
    except:
        pass

    try:
        # Plano C: Tenta Yahoo se o Fundamentus falhar
        t_yf = f"{t_fund}.SA"
        acao = yf.Ticker(t_yf)
        inf = acao.info
        return {
            "pl": inf.get('forwardPE') or inf.get('trailingPE') or 0.0,
            "dy": (inf.get('dividendYield') or 0.0) * 100,
            "margem": (inf.get('profitMargins') or 0.0) * 100,
            "fonte": "Yahoo Finance"
        }
    except:
        return None

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker_raw):
    """Busca preços garantindo o sufixo .SA"""
    t_yf = ticker_raw if ".SA" in ticker_raw.upper() else f"{ticker_raw.upper()}.SA"
    
    try:
        df = yf.download(t_yf, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df is None or df.empty: return None
        
        # Ajuste para SMTO3 e outros (MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data', 'High': 'maxima'}, inplace=True)
        
        close_series = df['fechamento']
        if len(close_series.shape) > 1: close_series = close_series.iloc[:, 0]

        # Cálculos Técnicos
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['sma_50'] = close_series.rolling(window=50).mean()
        
        return df.dropna()
    except: return None

# ==========================================
# 3. INTERFACE E EXECUÇÃO
# ==========================================
st.sidebar.header("⚙️ Parâmetros")
with st.sidebar.form("form_gestor"):
    SIMBOLO = st.text_input("Ação (Ex: ALOS3)", value="ALOS3").strip()
    st.divider()
    POSSUO = st.checkbox("Já possuo?")
    COMPRA = st.number_input("Preço Compra", value=0.0)
    STOP_PCT = st.number_input("Stop Loss %", value=5.0) / 100
    RSI_MAX = st.number_input("RSI Máx Entrada", value=55)
    btn = st.form_submit_button("🚀 ANALISAR")

st.title("🏢 Conselheiro B3: Gestor de Posição")
st.divider()

if btn:
    with st.spinner("Analisando mercado..."):
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos_alternativo(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            p_atual = float(atual['fechamento'].iloc[0]) if isinstance(atual['fechamento'], pd.Series) else float(atual['fechamento'])
            rsi = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            max180 = float(df['maxima'].tail(180).max())

            # Dash
            c1, c2, c3 = st.columns(3)
            c1.metric("Preço", f"R$ {p_atual:.2f}")
            c2.metric("RSI", f"{rsi:.1f}")
            c3.metric("Máx 180d", f"R$ {max180:.2f}")

            # Parecer
            st.subheader("📢 Parecer")
            if rsi > 70: st.warning("⚠️ SOBRECOMPRADO")
            elif p_atual > m50 and rsi < RSI_MAX: st.success("🟢 COMPRA/APORTE")
            elif p_atual < m50: st.error("🔴 TENDÊNCIA DE BAIXA")
            else: st.info("🟡 NEUTRO")

            # Fundamentos
            st.divider()
            if fund:
                st.subheader(f"🏥 Saúde ({fund['fonte']})")
                f1, f2, f3 = st.columns(3)
                f1.metric("P/L", f"{fund['pl']:.1f}")
                f2.metric("DY", f"{fund['dy']:.2f}%")
                f3.metric("Margem", f"{fund['margem']:.1f}%")
            else:
                st.info("ℹ️ Fundamentos indisponíveis no momento.")

            # Risco
            st.divider()
            st.subheader("🛡️ Gestão de Risco")
            st.error(f"Stop Loss: R$ {p_atual * (1-STOP_PCT):.2f}")
            st.success(f"Alvo (+15%): R$ {p_atual * 1.15:.2f}")
        else:
            st.error("Erro técnico. Verifique o ticker ou a conexão.")
