import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Radar B3 - Estratégico", page_icon="🎯", layout="wide")

# ==========================================
# 2. FUNÇÕES DE SUPORTE
# ==========================================

@st.cache_data(ttl=3600)
def checar_fundamentos(ticker_nome):
    """Busca saúde financeira usando apenas o texto do ticker para evitar erro de cache"""
    try:
        # Cria o objeto dentro da função para o Streamlit conseguir fazer o hash do parâmetro texto
        ticker_obj = yf.Ticker(ticker_nome)
        inf = ticker_obj.info
        
        if not inf or len(inf) < 10:
            return False, "Dados indisponíveis (Yahoo Limit)"
        
        # Coleta de indicadores fundamentais
        pl = inf.get('forwardPE') or inf.get('trailingPE') or 0.0
        dy = (inf.get('dividendYield') or 0.0) * 100
        margem = (inf.get('profitMargins') or 0.0) * 100
        
        # Critério de saúde: P/L positivo e Margem acima de 10%
        saudavel = (pl > 0 and margem > 10)
        status_texto = f"P/L: {pl:.1f} | DY: {dy:.1f}% | Margem: {margem:.1f}%"
        
        return saudavel, status_texto
    except:
        return False, "Indisponível no momento"

@st.cache_data(ttl=300)
def buscar_dados_tecnicos(ticker):
    """Busca preços e calcula indicadores técnicos (RSI e Média 50)"""
    try:
        # Força o sufixo .SA para o Yahoo Finance
        t_yf = ticker if ".SA" in ticker.upper() else f"{ticker.upper()}.SA"
        
        df = yf.download(t_yf, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: return None
        
        # Tratamento para ativos com colunas duplicadas (como SMTO3)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().reset_index()
        df.rename(columns={'Close': 'fechamento', 'Date': 'data'}, inplace=True)
        
        close_series = df['fechamento']
        if len(close_series.shape) > 1:
            close_series = close_series.iloc[:, 0]
        
        # Média Móvel de 50 dias
        df['sma_50'] = close_series.rolling(window=50).mean()
        
        # RSI (14 períodos)
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df.dropna()
    except:
        return None

# ==========================================
# 3. INTERFACE PRINCIPAL
# ==========================================
st.title("🎯 Radar B3: Oportunidades Estratégicas")
st.markdown("Monitorando ativos em **Tendência de Alta** (Preço > M50) com **RSI < 55** (Zona de Desconto).")

# Lista de ativos monitorados
ACOES_MONITORADAS = [
    'ALOS3.SA', 'SMTO3.SA', 'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 
    'BBDC4.SA', 'ABEV3.SA', 'WEGE3.SA', 'B3SA3.SA', 'RENT3.SA'
]

if st.button("🚀 INICIAR VARREDURA DO MERCADO", use_container_width=True):
    oportunidades = []
    barra_progresso = st.progress(0)
    
    for idx, ticker in enumerate(ACOES_MONITORADAS):
        # Atualiza o progresso na tela
        barra_progresso.progress((idx + 1) / len(ACOES_MONITORADAS))
        
        df_tec = buscar_dados_tecnicos(ticker)
        
        if df_tec is not None:
            atual = df_tec.iloc[-1]
            p_atual = float(atual['fechamento'])
            m50 = float(atual['sma_50'])
            rsi_val = float(atual['rsi'])
            
            # FILTRO DO SETUP: Tendência de Alta + RSI Favorável
            if p_atual > m50 and rsi_val < 55:
                # Se a técnica deu ok, verifica os fundamentos (passando apenas o texto do ticker)
                is_saudavel, texto_fund = checar_fundamentos(ticker)
                
                oportunidades.append({
                    "Ativo": ticker,
                    "Preço Atual": f"R$ {p_atual:.2f}",
                    "RSI (14d)": f"{rsi_val:.1f}",
                    "Saúde": "✅ Saudável" if is_saudavel else "⚠️ Alerta",
                    "Indicadores": texto_fund
                })
    
    barra_progresso.empty()
    
    # Exibição dos Resultados
    if oportunidades:
        st.success(f"Foram encontradas {len(oportunidades)} ações dentro do setup!")
        # Converte para DataFrame para uma exibição limpa em tabela
        df_final = pd.DataFrame(oportunidades)
        st.table(df_final)
    else:
        st.info("Nenhum ativo da lista preenche os critérios de compra no momento.")

st.divider()
st.caption("Aviso: Esta ferramenta é apenas para fins de estudo técnico e não constitui recomendação de investimento.")
