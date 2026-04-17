import streamlit as st
import ccxt
import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar Crypto", page_icon="📡", layout="centered")

st.title("📡 Radar Crypto")
st.markdown("Scanner automático de **Pullbacks (Correções)** no Gráfico Diário.")
st.markdown("---")

# LISTA ATUALIZADA: TSM agora aponta para o ticker correto do Yahoo
PORTFOLIO = {
    'SOL/USDT': 'SOL-USD',
    'BTC/USDT': 'BTC-USD',
    'ETH/USDT': 'ETH-USD',
    'AVAX/USDT': 'AVAX-USD',
    'LINK/USDT': 'LINK-USD',
    'ADA/USDT': 'ADA-USD',
    'DOGE/USDT': 'DOGE-USD',
    'DOT/USDT': 'DOT-USD',
    'XRP/USDT': 'XRP-USD',
    'POL/USDT': 'POL-USD',
    'ENJ/USDT': 'ENJ-USD',
    'XAUT/USDT': 'XAUT-USD',
    'ORDI/USDT': 'ORDI-USD',
    'BASED/USDT': 'BASED-USD',
    'TSM': 'TSM' # Alterado para o Radar entender que é Especial
}

# ==========================================
# 2. MOTOR DE DADOS (HÍBRIDO OKX / YAHOO)
# ==========================================
@st.cache_data(ttl=300)
def obter_dados_hibrido(simbolo_okx, simbolo_yf):
    # CASO ESPECIAL: TSM (Busca no Yahoo Finance)
    if simbolo_okx == 'TSM':
        df_yf = yf.download(simbolo_yf, period='150d', interval='1d', progress=False)
        if df_yf.empty: return None
        # Ajuste para garantir que as colunas sejam simples (não MultiIndex)
        if isinstance(df_yf.columns, pd.MultiIndex):
            df_yf.columns = df_yf.columns.get_level_values(0)
        
        df = df_yf[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.columns = ['abertura', 'maxima', 'minima', 'fechamento', 'volume']
    
    # CASO PADRÃO: Criptos (Busca na OKX)
    else:
        corretora = ccxt.okx()
        velas = corretora.fetch_ohlcv(simbolo_okx, '1d', limit=100)
        df = pd.DataFrame(velas, columns=['timestamp', 'abertura', 'maxima', 'minima', 'fechamento', 'volume'])
    
    # CÁLCULOS TÉCNICOS (Iguais para ambos)
    df['ema_rapida'] = df['fechamento'].ewm(span=9, adjust=False).mean()
    df['sma_50'] = df['fechamento'].rolling(window=50).mean()
    
    delta = df['fechamento'].diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = ganho / perda
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df.dropna()

# ==========================================
# 3. INTERFACE E EXECUÇÃO
# ==========================================
if st.button("🚀 Iniciar Varredura do Mercado", type="primary", use_container_width=True):
    resultados = []
    barra_progresso = st.progress(0)
    status_texto = st.empty()
    
    total = len(PORTFOLIO)
    for i, (simbolo_okx, simbolo_yf) in enumerate(PORTFOLIO.items()):
        status_texto.text(f"Analisando {simbolo_okx}...")
        
        try:
            # Usa a nova função híbrida
            df = obter_dados_hibrido(simbolo_okx, simbolo_yf)
            
            if df is None or df.empty:
                resultados.append({"Ativo": simbolo_okx, "Status": "⚠️ ERRO", "Detalhe": "Dados não encontrados.", "Preço": "-", "RSI": "-"})
                continue

            atual = df.iloc[-1]
            anterior = df.iloc[-2]
            
            tendencia_alta = atual['fechamento'] > atual['sma_50']
            em_promocao = atual['rsi'] < 55
            rompeu_ema9 = atual['fechamento'] > atual['ema_rapida'] and anterior['fechamento'] <= anterior['ema_rapida']
            
            preco = atual['fechamento']
            rsi = atual['rsi']
            
            if tendencia_alta and em_promocao and rompeu_ema9:
                resultados.append({"Ativo": simbolo_okx, "Status": "🚀 GATILHO DE COMPRA!", "Detalhe": "Pullback concluído. Cruzamento de EMA9 confirmado.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
            elif tendencia_alta and em_promocao and not rompeu_ema9:
                resultados.append({"Ativo": simbolo_okx, "Status": "👀 EM OBSERVAÇÃO", "Detalhe": "Em zona de desconto, aguardando virada da média rápida.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
            elif tendencia_alta and not em_promocao:
                resultados.append({"Ativo": simbolo_okx, "Status": "⏳ ESTICADA", "Detalhe": "RSI alto. Aguarde retornar às médias.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
            else:
                resultados.append({"Ativo": simbolo_okx, "Status": "🔴 TENDÊNCIA DE BAIXA", "Detalhe": "Abaixo da média de 50 dias.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
        
        except Exception as e:
            resultados.append({"Ativo": simbolo_okx, "Status": "⚠️ ERRO", "Detalhe": f"Falha: {str(e)}", "Preço": "-", "RSI": "-"})
                
        barra_progresso.progress((i + 1) / total)
        
    status_texto.empty()
    barra_progresso.empty()
    
    st.subheader("📊 Resultados de Hoje")
    
    for res in resultados:
        if "GATILHO" in res["Status"]:
            st.success(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
        elif "OBSERVAÇÃO" in res["Status"]:
            st.info(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
        elif "ESTICADA" in res["Status"]:
            st.warning(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
        else:
            st.error(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
else:
    st.write("Clique no botão acima para iniciar a análise da carteira.")
