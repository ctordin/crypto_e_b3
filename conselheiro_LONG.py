import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 1. CONFIGURAÇÃO DA PÁGINA WEB (Sempre a primeira linha)
st.set_page_config(page_title="Conselheiro Quantitativo", page_icon="🤖", layout="centered")

# ==========================================
# 2. BARRA LATERAL (MENU INTERATIVO)
# ==========================================
st.sidebar.header("⚙️ Parâmetros do Ativo")
# Agora você digita a moeda direto no navegador!
SIMBOLO = st.sidebar.text_input("Símbolo (ex: SOL/USDT)", value="SOL/USDT").upper()
TIMEFRAME = st.sidebar.selectbox("Tempo Gráfico", ["1d", "4h", "1h"], index=0)

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Gestão de Risco (Gabarito)")
# Você ajusta os stops por barrinhas na tela
STOP_LOSS_PCT = st.sidebar.number_input("Stop Loss (%)", min_value=1.0, max_value=20.0, value=4.0, step=1.0) / 100.0
TRAILING_STOP_PCT = st.sidebar.number_input("Trailing Stop (%)", min_value=1.0, max_value=50.0, value=20.0, step=1.0) / 100.0
RSI_MAX_ENTRADA = st.sidebar.number_input("RSI Máx. (Promoção)", min_value=30, max_value=80, value=52, step=1)

# ==========================================
# 3. LÓGICA DE DADOS (Motor Quantitativo)
# ==========================================
# O st.cache_data evita que o app fique baixando dados à toa toda vez que você clica em algo
@st.cache_data(ttl=300) 
def obter_dados(simbolo, timeframe):
    corretora = ccxt.okx()
    velas = corretora.fetch_ohlcv(simbolo, timeframe, limit=100)
    df = pd.DataFrame(velas, columns=['timestamp', 'abertura', 'maxima', 'minima', 'fechamento', 'volume'])
    
    df['ema_rapida'] = df['fechamento'].ewm(span=9, adjust=False).mean()
    df['ema_lenta'] = df['fechamento'].ewm(span=21, adjust=False).mean()
    df['sma_50'] = df['fechamento'].rolling(window=50).mean()
    
    delta = df['fechamento'].diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = ganho / perda
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df.dropna()

# ==========================================
# 4. INTERFACE PRINCIPAL
# ==========================================
st.title("🤖 Conselheiro Quantitativo")
st.markdown("Transforme os dados do Otimizador em ordens precisas de compra.")
st.markdown("---")

if st.sidebar.button("Analisar Ativo", type="primary", use_container_width=True):
    with st.spinner(f"A conectar aos servidores da OKX para analisar {SIMBOLO}..."):
        try:
            df = obter_dados(SIMBOLO, TIMEFRAME)
            atual = df.iloc[-1]
            anterior = df.iloc[-2]

            preco = atual['fechamento']

            # Verificações da Estratégia de Pullback
            tendencia_alta = preco > atual['sma_50']
            moeda_corrigiu = atual['rsi'] < RSI_MAX_ENTRADA
            rompeu_ema9 = preco > atual['ema_rapida'] and anterior['fechamento'] <= anterior['ema_rapida']

            valor_stop_loss = preco * (1 - STOP_LOSS_PCT)
            valor_alvo_trailing = preco * (1 + TRAILING_STOP_PCT)

            # Lógica de Recomendação com cores para o Streamlit
            if tendencia_alta and moeda_corrigiu and rompeu_ema9:
                recomendacao = "🟢 COMPRA IMEDIATA (Gatilho Acionado!)"
                status = "O ativo está em tendência de alta, corrigiu o suficiente e retomou a força hoje."
                alerta = st.success
            elif tendencia_alta and moeda_corrigiu and not rompeu_ema9:
                recomendacao = "👀 PREPARAR COMPRA (Aguardar Gatilho)"
                status = "O ativo tem um excelente desconto, mas ainda está a cair. Aguarde o preço fechar acima da EMA 9."
                alerta = st.info
            elif tendencia_alta and not moeda_corrigiu:
                recomendacao = "⏳ MANTER / NÃO COMPRAR MAIS (Esticado)"
                status = "O ativo já subiu bastante. Se tem a moeda, deixe o Trailing Stop rolar. Se não, fique de fora."
                alerta = st.warning
            else:
                recomendacao = "🔴 FORA DO MERCADO (Tendência de Baixa)"
                status = "A maré está contra. O preço está abaixo da Média Macro de 50 dias. Risco elevado."
                alerta = st.error

            # Renderizando a resposta na tela
            st.subheader(recomendacao)
            alerta(status)

            st.markdown("### 📊 Radiografia do Ativo")
            # st.columns cria blocos organizados lado a lado
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"${preco:.2f}")
            col2.metric("Média Macro (50)", f"${atual['sma_50']:.2f}", "Alta" if preco > atual['sma_50'] else "-Baixa")
            col3.metric(f"RSI (Max {RSI_MAX_ENTRADA})", f"{atual['rsi']:.1f}", "Promoção" if atual['rsi'] < RSI_MAX_ENTRADA else "-Caro")

            # Exibe os alvos apenas se houver viés de compra
            if "COMPRA" in recomendacao:
                st.markdown("### 🛡️ Gestão de Risco Estrita")
                st.info("Copie estes valores e cole na sua corretora para proteger a operação.")
                col4, col5 = st.columns(2)
                col4.metric(f"Onde colocar o Stop Loss (-{STOP_LOSS_PCT*100:.0f}%)", f"${valor_stop_loss:.2f}")
                col5.metric(f"Alvo para ativar Trailing (+{TRAILING_STOP_PCT*100:.0f}%)", f"${valor_alvo_trailing:.2f}")

            st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        except Exception as e:
            st.error(f"Erro ao buscar dados na corretora. Verifique se o símbolo está correto (ex: BTC/USDT). Detalhes: {e}")
else:
    # Tela inicial antes do usuário clicar no botão
    st.write("👈 Configure os parâmetros do Otimizador no menu lateral e clique em **Analisar Ativo**.")
