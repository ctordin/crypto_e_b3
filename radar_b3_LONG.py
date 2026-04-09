import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar B3", page_icon="🏢", layout="centered")

st.title("🏢 Radar B3")
st.markdown("Scanner de **Pullbacks** para ações da Bolsa Brasileira (Gráfico Diário).")
st.markdown("---")

LISTA_ACOES = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'MGLU3.SA', 'MULT3.SA',
    'WEGE3.SA', 'ABEV3.SA', 'RENT3.SA', 'SUZB3.SA', 'MDNE3.SA',
    'ALOS3.SA'
]

# ==========================================
# 2. MOTOR DE DADOS (VERSÃO BLINDADA)
# ==========================================
@st.cache_data(ttl=300)
def obter_dados_b3(ticker):
    try:
        # 150 dias para garantir a média de 50
        df = yf.download(ticker, period='150d', interval='1d', progress=False)
        
        if df.empty or len(df) < 50: 
            return None
        
        # Tratamento Universal de Colunas (Achatamento de MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        
        df = df.reset_index()
        
        # Mapeamento de Fechamento (Adj Close ou Close)
        if 'Adj Close' in df.columns:
            df.rename(columns={'Adj Close': 'fechamento'}, inplace=True)
        elif 'Close' in df.columns:
            df.rename(columns={'Close': 'fechamento'}, inplace=True)
            
        df.rename(columns={'Date': 'data'}, inplace=True)
        
        # Indicadores
        df['ema_rapida'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df.dropna()
    except:
        return None

# ==========================================
# 3. INTERFACE E EXECUÇÃO
# ==========================================
if st.button("🔍 Varrer Mercado Brasileiro", type="primary", use_container_width=True):
    resultados = []
    
    barra_progresso = st.progress(0)
    status_texto = st.empty()
    
    total = len(LISTA_ACOES)
    for i, acao in enumerate(LISTA_ACOES):
        status_texto.text(f"Analisando comportamento de {acao}...")
        
        df = obter_dados_b3(acao)
        nome = acao.replace('.SA', '')
        
        if df is None:
            resultados.append({"Ativo": nome, "Status": "⚠️ ERRO", "Detalhe": "Dados insuficientes ou ticker inválido.", "Preço": "-", "RSI": "-"})
        else:
            atual = df.iloc[-1]
            anterior = df.iloc[-2]
            
            preco = float(atual['fechamento'])
            rsi = float(atual['rsi'])
            
            tendencia_alta = preco > float(atual['sma_50'])
            em_promocao = rsi < 55
            rompeu_ema9 = preco > float(atual['ema_rapida']) and float(anterior['fechamento']) <= float(anterior['ema_rapida'])
            
            if tendencia_alta and em_promocao and rompeu_ema9:
                resultados.append({"Ativo": nome, "Status": "🚀 GATILHO DE COMPRA!", "Detalhe": "Ação em alta macro, com desconto e retomando força hoje.", "Preço": f"R${preco:.2f}", "RSI": f"{rsi:.1f}"})
            elif tendencia_alta and em_promocao and not rompeu_ema9:
                resultados.append({"Ativo": nome, "Status": "👀 EM OBSERVAÇÃO", "Detalhe": "Ação barata, mas ainda sem sinal de retomada. Aguarde fechar acima da EMA 9.", "Preço": f"R${preco:.2f}", "RSI": f"{rsi:.1f}"})
            elif tendencia_alta and not em_promocao:
                resultados.append({"Ativo": nome, "Status": "⏳ ESTICADA", "Detalhe": "Ação já subiu muito. Aguarde uma correção saudável (Pullback).", "Preço": f"R${preco:.2f}", "RSI": f"{rsi:.1f}"})
            else:
                resultados.append({"Ativo": nome, "Status": "🔴 TENDÊNCIA DE BAIXA", "Detalhe": "O preço está abaixo da Média de 50 dias. Risco de queda livre.", "Preço": f"R${preco:.2f}", "RSI": f"{rsi:.1f}"})
        
        barra_progresso.progress((i + 1) / total)
        
    status_texto.empty()
    barra_progresso.empty()
    
    st.subheader("📊 Relatório de Oportunidades")
    
    for res in resultados:
        # Layout de exibição no Streamlit
        with st.container():
            if "GATILHO" in res["Status"]:
                st.success(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
            elif "OBSERVAÇÃO" in res["Status"]:
                st.info(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
            elif "ESTICADA" in res["Status"]:
                st.warning(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
            else:
                st.error(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")

    st.markdown("---")
    st.caption(f"Varredura finalizada em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
else:
    st.write("Clique no botão acima para analisar as principais ações da sua carteira na B3.")
