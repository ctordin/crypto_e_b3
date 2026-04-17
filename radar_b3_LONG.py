import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Radar B3 - Estratégico", page_icon="🎯", layout="wide")

# ==========================================
# 2. FUNÇÕES DE SUPORTE (DEFINIDAS NO TOPO)
# ==========================================

@st.cache_data(ttl=3600)
def checar_fundamentos(ticker_obj):
    """Verifica saúde financeira sem travar o app se o Yahoo bloquear"""
    try:
        inf = ticker_obj.info
        if not inf or len(inf) < 10:
            return False, "Dados indisponíveis (Yahoo Limit)"
        
        # Critérios simples de saúde
        pl = inf.get('forwardPE') or inf.get('trailingPE') or 0
        dy = (inf.get('dividendYield') or 0) * 100
        margem = (inf.get('profitMargins') or 0) * 100
        
        status = "SAUDÁVEL" if pl > 0 and margem > 10 else "ALERTA"
        texto = f"P/L: {pl:.1f} | DY: {dy:.1f}% | Margem: {margem:.1f}%"
        return (status == "SAUDÁVEL"), texto
    except:
        return False, "Indisponível no momento"

@st.cache_data(ttl=300)
def buscar_dados(ticker):
    """Busca preços e calcula RSI/Média 50"""
    try:
        df = yf.download(ticker, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: return None
        
        # Limpeza de colunas (essencial para ativos como SMTO3)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data'}, inplace=True)
        
        # Cálculos
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
# 3. INTERFACE E PROCESSAMENTO
# ==========================================
st.title("🎯 Radar B3: Oportunidades de Compra")
st.markdown("Busca ativos acima da **Média de 50** com **RSI abaixo de 55**.")

# Lista de ações para monitorar (adicione as que desejar)
ACOES = ['ALOS3.SA', 'SMTO3.SA', 'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 'BBDC4.SA', 'ABEV3.SA']

if st.button("🚀 INICIAR VARREDURA"):
    resultados = []
    progresso = st.progress(0)
    
    for i, acao_ticker in enumerate(ACOES):
        progresso.progress((i + 1) / len(ACOES))
        
        df = buscar_dados(acao_ticker)
        if df is not None:
            atual = df.iloc[-1]
            p_atual = float(atual['fechamento'])
            m50 = float(atual['sma_50'])
            rsi = float(atual['rsi'])
            
            # Condição de Compra do seu setup
            if p_atual > m50 and rsi < 55:
                # Tenta buscar fundamentos agora que a técnica passou
                ticker_obj = yf.Ticker(acao_ticker)
                saudavel, texto_fund = checar_fundamentos(ticker_obj)
                
                resultados.append({
                    "Ticker": acao_ticker,
                    "Preço": f"R$ {p_atual:.2f}",
                    "RSI": f"{rsi:.1f}",
                    "Saúde": "✅" if saudavel else "⚠️",
                    "Indicadores": texto_fund
                })
    
    progresso.empty()
    
    if resultados:
        st.success(f"Encontradas {len(resultados)} oportunidades!")
        st.table(pd.DataFrame(resultados))
    else:
        st.info("Nenhuma ação atingiu os critérios de setup no momento.")
