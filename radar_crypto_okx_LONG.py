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
    'POL/USDT': 'POL-USD'
}

# ==========================================
# 2. MOTOR DE DADOS
# ==========================================
@st.cache_data(ttl=300)
def checar_fundamentos(ticker_yf):
    try:
        info = yf.Ticker(ticker_yf).info
        mkt_cap = info.get('marketCap', 1)
        vol_24h = info.get('volume24Hr', 0)
        giro_diario = (vol_24h / mkt_cap) * 100
        return giro_diario > 2.0
    except:
        return True 

@st.cache_data(ttl=300)
def obter_dados(simbolo):
    corretora = ccxt.okx()
    velas = corretora.fetch_ohlcv(simbolo, '1d', limit=100)
    df = pd.DataFrame(velas, columns=['timestamp', 'abertura', 'maxima', 'minima', 'fechamento', 'volume'])
    
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
    
    # Animações de progresso para a Web
    barra_progresso = st.progress(0)
    status_texto = st.empty()
    
    total = len(PORTFOLIO)
    for i, (simbolo_okx, simbolo_yf) in enumerate(PORTFOLIO.items()):
        status_texto.text(f"A descarregar dados e a analisar {simbolo_okx}...")
        
        if not checar_fundamentos(simbolo_yf):
            resultados.append({
                "Ativo": simbolo_okx, "Status": "❌ REPROVADA", 
                "Detalhe": "A moeda não possui liquidez diária suficiente para operar com segurança.", 
                "Preço": "-", "RSI": "-"
            })
        else:
            try:
                df = obter_dados(simbolo_okx)
                atual = df.iloc[-1]
                anterior = df.iloc[-2]
                
                tendencia_alta = atual['fechamento'] > atual['sma_50']
                em_promocao = atual['rsi'] < 55
                rompeu_ema9 = atual['fechamento'] > atual['ema_rapida'] and anterior['fechamento'] <= anterior['ema_rapida']
                
                preco = atual['fechamento']
                rsi = atual['rsi']
                
                if tendencia_alta and em_promocao and rompeu_ema9:
                    resultados.append({"Ativo": simbolo_okx, "Status": "🚀 GATILHO DE COMPRA!", "Detalhe": "A maré está a subir, a moeda ficou barata e os compradores acabaram de voltar.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
                elif tendencia_alta and em_promocao and not rompeu_ema9:
                    resultados.append({"Ativo": simbolo_okx, "Status": "👀 EM OBSERVAÇÃO", "Detalhe": "O preço está com grande desconto, mas ainda está a cair. Aguarde romper a EMA 9.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
                elif tendencia_alta and not em_promocao:
                    resultados.append({"Ativo": simbolo_okx, "Status": "⏳ ESTICADA", "Detalhe": "A moeda já subiu bastante recentemente. Aguarde uma correção.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
                else:
                    resultados.append({"Ativo": simbolo_okx, "Status": "🔴 TENDÊNCIA DE BAIXA", "Detalhe": "O preço está a negociar abaixo da Média Macro de 50 dias.", "Preço": f"${preco:.2f}", "RSI": f"{rsi:.1f}"})
            except Exception as e:
                resultados.append({"Ativo": simbolo_okx, "Status": "⚠️ ERRO", "Detalhe": f"Falha na corretora: {str(e)}", "Preço": "-", "RSI": "-"})
                
        # Atualiza a barra de carregamento
        barra_progresso.progress((i + 1) / total)
        
    # Limpa a barra quando termina
    status_texto.empty()
    barra_progresso.empty()
    
    st.subheader("📊 Resultados de Hoje")
    
    # Exibir os blocos coloridos no Streamlit
    for res in resultados:
        if "GATILHO" in res["Status"]:
            st.success(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
        elif "OBSERVAÇÃO" in res["Status"]:
            st.info(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
        elif "ESTICADA" in res["Status"]:
            st.warning(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
        else:
            st.error(f"**{res['Ativo']}** | {res['Status']} \n\nPreço: {res['Preço']} | RSI: {res['RSI']} \n\n*{res['Detalhe']}*")
            
    st.markdown("---")
    st.info("🎯 **DICA:** Se alguma moeda acusou **GATILHO DE COMPRA**, abra o seu aplicativo **Conselheiro Crypto** para inserir essa moeda e descobrir onde colocar o Stop Loss exato!")
else:
    # O que aparece antes de clicar no botão
    st.write("Clique no botão acima para descarregar os dados da OKX e analisar toda a sua carteira.")
