import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro B3 Gestor", page_icon="🏢", layout="wide")

# ==========================================
# 2. FUNÇÕES DE BUSCA
# ==========================================

@st.cache_data(ttl=3600)
def buscar_fundamentos(ticker):
    """Tenta buscar fundamentos. Se o Yahoo bloquear (N/A), retorna None."""
    try:
        acao = yf.Ticker(ticker)
        inf = acao.info
        if not inf or len(inf) < 5: return None
        
        return {
            "pl": inf.get('forwardPE') or inf.get('trailingPE') or 0.0,
            "dy": (inf.get('dividendYield') or 0.0) * 100,
            "margem": (inf.get('profitMargins') or 0.0) * 100
        }
    except:
        return None

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker):
    try:
        df = yf.download(ticker, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'High': 'maxima', 'Volume': 'volume'}, inplace=True)
        
        close_series = df['fechamento']
        if len(close_series.shape) > 1: close_series = close_series.iloc[:, 0]
        
        # Indicadores Técnicos
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
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
        STOP_PCT = st.number_input("Stop Loss desejado (%)", value=5.0) / 100.0
        RSI_MAX = st.number_input("RSI Máx. (Entrada)", value=55)
        btn_analisar = st.form_submit_button("🚀 ANALISAR AGORA", use_container_width=True)

# ==========================================
# 4. PAINEL PRINCIPAL (LAYOUT CRYPTO)
# ==========================================
st.title("🏢 Conselheiro B3: Gestor de Posição")

if btn_analisar:
    with st.spinner("Sincronizando dados técnicos e fundamentalistas..."):
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            p_atual = float(atual['fechamento'])
            rsi_val = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            vol_atual = float(atual['volume'])
            vol_medio = float(df['volume'].tail(20).mean())
            
            # Máximas
            max90 = float(df['maxima'].tail(90).max())
            max180 = float(df['maxima'].tail(180).max())

            # --- LINHA 1: MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            c1.caption("Preço Atual")
            c1.subheader(f"R$ {p_atual:.2f}")
            c2.caption("RSI (14d)")
            c2.subheader(f"{rsi_val:.1f}")
            c3.caption("Volume")
            status_vol = "Alto" if vol_atual > vol_medio else "Normal"
            c3.subheader(status_vol)

            st.divider()

            # --- LINHA 2: SAÚDE FINANCEIRA (FUNDAMENTOS) ---
            st.markdown("### 🏥 Saúde da Empresa")
            if fund:
                f1, f2, f3 = st.columns(3)
                f1.metric("P/L", f"{fund['pl']:.1f}" if fund['pl'] > 0 else "N/A")
                f2.metric("Div. Yield", f"{fund['dy']:.2f}%" if fund['dy'] > 0 else "N/A")
                f3.metric("Margem", f"{fund['margem']:.1f}%" if fund['margem'] > 0 else "N/A")
            else:
                st.info("ℹ️ Indicadores fundamentalistas temporariamente indisponíveis no Yahoo.")
            
            st.divider()

            # --- LINHA 3: RADIOGRAFIA ---
            st.markdown("### 📊 Radiografia do Mercado")
            r1, r2 = st.columns(2)
            r1.info(f"Máxima 90 dias: R$ {max90:.4f}")
            r2.info(f"Máxima 180 dias: R$ {max180:.4f}")

            # --- PARECER TÉCNICO ---
            if rsi_val > 70:
                st.warning(f"🟡 SOBRECOMPRADO: RSI em {rsi_val:.1f}. Aguarde correção.")
            elif p_atual > m50 and rsi_val < RSI_MAX:
                st.success(f"🟢 COMPRA/APORTE: Tendência de alta confirmada.")
            elif p_atual < m50:
                st.error(f"🔴 TENDÊNCIA DE BAIXA: Preço abaixo da Média de 50 dias.")
            else:
                st.info("🟡 NEUTRO: Aguarde definição de volume ou RSI.")

            st.divider()

            # --- LINHA 4: GESTÃO DE SAÍDA ---
            st.markdown("### 💔 Gestão de Saída / Stop Loss")
            v_stop = p_atual * (1 - STOP_PCT)
            v_alvo = p_atual * 1.20 
            
            g1, g2 = st.columns(2)
            g1.error(f"Stop Loss Sugerido: R$ {v_stop:.4f}")
            g2.success(f"Alvo Sugerido (+20%): R$ {v_alvo:.4f}")

            # --- ANÁLISE DE CICLO ---
            dist_180 = ((max180 - p_atual) / max180) * 100
            st.markdown(f"**Análise de Ciclo:** O preço atual está a **{dist_180:.1f}%** abaixo da máxima de 180 dias.")

        else:
            st.error("Erro ao carregar dados. Verifique o ticker (ex: PETR4.SA).")
