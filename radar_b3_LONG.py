import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Radar B3 - Lista Expandida", page_icon="🎯", layout="wide")

# ==========================================
# 2. FUNÇÕES DE SUPORTE
# ==========================================

@st.cache_data(ttl=3600)
def checar_fundamentos(ticker_nome):
    """Busca saúde financeira de forma estável"""
    try:
        ticker_obj = yf.Ticker(ticker_nome)
        inf = ticker_obj.info
        if not inf or len(inf) < 10:
            return False, "Dados indisponíveis (Yahoo Limit)"
        
        pl = inf.get('forwardPE') or inf.get('trailingPE') or 0.0
        dy = (inf.get('dividendYield') or 0.0) * 100
        margem = (inf.get('profitMargins') or 0.0) * 100
        
        saudavel = (pl > 0 and margem > 10)
        status_texto = f"P/L: {pl:.1f} | DY: {dy:.1f}% | Margem: {margem:.1f}%"
        return saudavel, status_texto
    except:
        return False, "Indisponível no momento"

@st.cache_data(ttl=300)
def buscar_dados_tecnicos(ticker):
    """Busca preços e calcula indicadores (RSI e M50)"""
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
# 3. INTERFACE E LISTA AMPLIADA
# ==========================================
st.title("🎯 Radar B3: Varredura de Mercado")
st.markdown("Monitorando as **25 maiores oportunidades** com base no seu setup técnico.")

# LISTA AMPLIADA - 25 ATIVOS
ACOES_MONITORADAS = [
    'ALOS3.SA', 'SMTO3.SA', 'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 
    'BBDC4.SA', 'ABEV3.SA', 'WEGE3.SA', 'B3SA3.SA', 'RENT3.SA',
    'BBAS3.SA', 'SANB11.SA', 'ELET3.SA', 'EQTL3.SA', 'VIVT3.SA',
    'CPLE6.SA', 'RAIZ4.SA', 'SUZB3.SA', 'JBSS3.SA', 'GGBR4.SA',
    'CSNA3.SA', 'PRIO3.SA', 'VBBR3.SA', 'RADL3.SA', 'LREN3.SA'
]

if st.button("🚀 INICIAR VARREDURA COMPLETA", use_container_width=True):
    oportunidades = []
    barra_progresso = st.progress(0)
    status_acao = st.empty() # Para mostrar qual ação está sendo lida
    
    for idx, ticker in enumerate(ACOES_MONITORADAS):
        barra_progresso.progress((idx + 1) / len(ACOES_MONITORADAS))
        status_acao.caption(f"Analisando: {ticker}...")
        
        df_tec = buscar_dados_tecnicos(ticker)
        
        if df_tec is not None:
            atual = df_tec.iloc[-1]
            p_atual = float(atual['fechamento'])
            m50 = float(atual['sma_50'])
            rsi_val = float(atual['rsi'])
            
            # FILTRO: Tendência de Alta + RSI < 55
            if p_atual > m50 and rsi_val < 55:
                is_saudavel, texto_fund = checar_fundamentos(ticker)
                
                oportunidades.append({
                    "Ativo": ticker,
                    "Preço Atual": f"R$ {p_atual:.2f}",
                    "RSI (14d)": f"{rsi_val:.1f}",
                    "Saúde": "✅ Saudável" if is_saudavel else "⚠️ Alerta",
                    "Indicadores": texto_fund
                })
    
    barra_progresso.empty()
    status_acao.empty()
    
   if oportunidades:
        st.success(f"Foram encontradas {len(oportunidades)} ações no ponto de compra!")
        
        # Transformando em DataFrame para formatar
        df_final = pd.DataFrame(oportunidades)
        
        # Exibindo com bordas horizontais e largura total conforme a documentação
        st.table(df_final, border="horizontal", width="stretch")
    else:
        st.info("Nenhuma das 25 ações preenche os critérios no momento.")
