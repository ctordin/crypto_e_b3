import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Radar B3 - Visão Geral", page_icon="🎯", layout="wide")

# ==========================================
# 2. FUNÇÃO DE BUSCA TÉCNICA
# ==========================================

@st.cache_data(ttl=300)
def buscar_dados_completos(ticker):
    try:
        t_yf = ticker if ".SA" in ticker.upper() else f"{ticker.upper()}.SA"
        df = yf.download(t_yf, period='250d', interval='1d', progress=False, auto_adjust=True)
        
        if df is None or df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data'}, inplace=True)
        
        close_series = df['fechamento']
        if len(close_series.shape) > 1: close_series = close_series.iloc[:, 0]
        
        # Cálculo dos indicadores
        df['sma_50'] = close_series.rolling(window=50).mean()
        
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df.dropna()
    except:
        return None

# ==========================================
# 3. INTERFACE E PROCESSAMENTO
# ==========================================
st.title("🎯 Radar B3: Painel de Monitoramento")
st.markdown("Lista completa com foco em **Tendência (M50)** e **Momento (RSI)**.")

ACOES_MONITORADAS = [
    'ALOS3.SA', 'SMTO3.SA', 'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 
    'BBDC4.SA', 'ABEV3.SA', 'WEGE3.SA', 'B3SA3.SA', 'RENT3.SA',
    'BBAS3.SA', 'SANB11.SA', 'ELET3.SA', 'EQTL3.SA', 'VIVT3.SA',
    'CPLE6.SA', 'RAIZ4.SA', 'SUZB3.SA', 'JBSS3.SA', 'GGBR4.SA',
    'CSNA3.SA', 'PRIO3.SA', 'VBBR3.SA', 'RADL3.SA', 'LREN3.SA'
]

if st.button("🚀 ATUALIZAR TODOS OS ATIVOS", use_container_width=True):
    painel_geral = []
    barra_progresso = st.progress(0)
    
    for idx, ticker in enumerate(ACOES_MONITORADAS):
        barra_progresso.progress((idx + 1) / len(ACOES_MONITORADAS))
        
        df = buscar_dados_completos(ticker)
        
        if df is not None:
            atual = df.iloc[-1]
            p_atual = float(atual['fechamento'])
            rsi_val = float(atual['rsi'])
            m50 = float(atual['sma_50'])
            
            # Parecer sobre a Média de 50
            if p_atual > m50:
                dist_m50 = ((p_atual - m50) / m50) * 100
                status_m50 = f"⬆️ ALTA (+{dist_m50:.1f}%)"
            else:
                dist_m50 = ((m50 - p_atual) / m50) * 100
                status_m50 = f"⬇️ BAIXA (-{dist_m50:.1f}%)"

            # Lógica de Recomendação Técnica
            if p_atual > m50 and rsi_val < 55:
                rec = "🟢 COMPRA ESTRATÉGICA"
            elif rsi_val > 70:
                rec = "🟡 ESTICADO (Aguardar)"
            elif p_atual < m50:
                rec = "🔴 FORA (Tendência Baixa)"
            else:
                rec = "⚪ NEUTRO"
                
            painel_geral.append({
                "Ativo": ticker,
                "Preço": f"R$ {p_atual:.2f}",
                "Parecer M50": status_m50,
                "RSI (14d)": f"{rsi_val:.1f}",
                "Recomendação": rec
            })
            
    barra_progresso.empty()
    
    if painel_geral:
        df_final = pd.DataFrame(painel_geral)
        # Exibição usando o st.table com bordas horizontais conforme a doc
        st.table(df_final)
    else:
        st.error("Erro ao carregar dados. Tente novamente.")

st.divider()
st.info("**Legenda M50:** Indica se o preço está acima ou abaixo da média de 50 dias e a distância percentual.")
