import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar B3 Fundamentalista", page_icon="🏢", layout="centered")

st.title("🏢 Radar B3 + Fundamentos")
st.markdown("Scanner de **Swing Trade**: Técnico (RSI/Médias) + Fundamentalista (P/L/Margem).")
st.markdown("---")

LISTA_ACOES = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA',
    'WEGE3.SA', 'ABEV3.SA', 'RENT3.SA', 'SUZB3.SA', 'RADL3.SA', 'ALOS3.SA'
]

# ==========================================
# 2. MOTOR DE ANÁLISE (TÉCNICO + FUNDAMENTOS)
# ==========================================
@st.cache_data(ttl=3600) # Dados fundamentalistas mudam pouco, cache de 1h
def checar_fundamentos(ticker):
    try:
        acao = yf.Ticker(ticker)
        info = acao.info
        
        # Filtros de Qualidade para Swing Trade
        pe_ratio = info.get('forwardPE') or info.get('trailingPE') or 0
        dy = (info.get('dividendYield') or 0) * 100
        margem = info.get('profitMargins') or 0
        
        # Critério: P/L abaixo de 25 e Margem Líquida positiva (>5%)
        # Isso remove empresas "bolhas" ou em prejuízo crônico
        is_saudavel = 0 < pe_ratio < 25 and margem > 0.05
        
        status_fund = f"P/L: {pe_ratio:.1f} | DY: {dy:.1f}% | Margem: {margem*100:.1f}%"
        return is_saudavel, status_fund
    except:
        return True, "Fundamentos: N/A (Erro na consulta)"

@st.cache_data(ttl=300)
def obter_dados_graficos(ticker):
    try:
        df = yf.download(ticker, period='150d', interval='1d', progress=False)
        if df.empty or len(df) < 50: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        
        df = df.reset_index()
        fechamento = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df.rename(columns={fechamento: 'fechamento', 'Date': 'data'}, inplace=True)
        
        # Indicadores
        df['ema_9'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (ganho/perda)))
        
        return df.dropna()
    except:
        return None

# ==========================================
# 3. INTERFACE E EXECUÇÃO
# ==========================================
if st.button("🔍 Iniciar Varredura Quantamental", type="primary", use_container_width=True):
    barra = st.progress(0)
    status_progresso = st.empty()
    
    for i, acao in enumerate(LISTA_ACOES):
        status_progresso.text(f"Analisando saúde e gráfico de {acao}...")
        nome = acao.replace('.SA', '')
        
        # 1. Checagem Fundamentalista
        saudavel, texto_fund = checar_fundamentos(acao)
        
        if not saudavel:
            st.error(f"**{nome}** | ❌ REPROVADA NOS FUNDAMENTOS\n\n*{texto_fund}*")
        else:
            # 2. Checagem Técnica (Gráfico)
            df = obter_dados_graficos(acao)
            if df is not None:
                atual = df.iloc[-1]
                anterior = df.iloc[-2]
                
                preco = float(atual['fechamento'])
                rsi = float(atual['rsi'])
                tendencia_alta = preco > float(atual['sma_50'])
                em_promocao = rsi < 55
                rompeu_ema9 = preco > float(atual['ema_9']) and float(anterior['fechamento']) <= float(anterior['ema_9'])
                
                # Exibição baseada no Gatilho
                if tendencia_alta and em_promocao and rompeu_ema9:
                    st.success(f"**{nome}** | 🚀 GATILHO TÉCNICO + FUNDAMENTOS OK!\n\nPreço: R${preco:.2f} | RSI: {rsi:.1f} | {texto_fund}")
                elif tendencia_alta and em_promocao:
                    st.info(f"**{nome}** | 👀 EM OBSERVAÇÃO (Barata, aguardando sinal)\n\nPreço: R${preco:.2f} | RSI: {rsi:.1f} | {texto_fund}")
                elif tendencia_alta and not em_promocao:
                    st.warning(f"**{nome}** | ⏳ ESTICADA (Aguarde recuo)\n\nPreço: R${preco:.2f} | RSI: {rsi:.1f} | {texto_fund}")
                else:
                    st.error(f"**{nome}** | 🔴 TENDÊNCIA DE BAIXA (Risco Alto)\n\nPreço: R${preco:.2f} | RSI: {rsi:.1f} | {texto_fund}")
            
        barra.progress((i + 1) / len(LISTA_ACOES))
    
    status_progresso.empty()
    st.success("Varredura finalizada!")
else:
    st.info("Clique no botão acima para rodar a análise técnica e fundamentalista da carteira B3.")
