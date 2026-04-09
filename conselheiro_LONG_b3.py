import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA WEB
# ==========================================
st.set_page_config(page_title="Conselheiro B3", page_icon="🏢", layout="centered")

# ==========================================
# 2. BARRA LATERAL (MENU INTERATIVO)
# ==========================================
st.sidebar.header("⚙️ Parâmetros da Ação")
st.sidebar.markdown("*(Lembre-se de colocar **.SA** no final do código)*")
# O .strip() garante que espaços vazios não causem erro na pesquisa
SIMBOLO = st.sidebar.text_input("Ação (ex: VALE3.SA, ITUB4.SA)", value="VALE3.SA").upper().strip()

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Gestão de Risco (Gabarito B3)")
# Valores padrão ajustados para a volatilidade típica da B3
STOP_LOSS_PCT = st.sidebar.number_input("Stop Loss (%)", min_value=1.0, max_value=15.0, value=5.0, step=1.0) / 100.0
TRAILING_STOP_PCT = st.sidebar.number_input("Trailing Stop (%)", min_value=1.0, max_value=30.0, value=10.0, step=1.0) / 100.0
RSI_MAX_ENTRADA = st.sidebar.number_input("RSI Máx. (Promoção)", min_value=30, max_value=80, value=55, step=1)

# ==========================================
# 3. LÓGICA DE DADOS (Motor Quantitativo Yahoo Finance)
# ==========================================
@st.cache_data(ttl=300) 
def obter_dados_b3(ticker):
    try:
        # Baixa 150 dias para garantir dados suficientes para a SMA 50
        df = yf.download(ticker, period='150d', interval='1d', progress=False)
        
        if df.empty or len(df) < 50: 
            return None
        
        # Tratamento Universal de Colunas (Evita o erro da VALE3)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        
        df = df.reset_index()
        
        # Mapeamento Dinâmico (Procura Adj Close primeiro, depois Close)
        if 'Adj Close' in df.columns:
            df.rename(columns={'Adj Close': 'fechamento'}, inplace=True)
        elif 'Close' in df.columns:
            df.rename(columns={'Close': 'fechamento'}, inplace=True)
            
        df.rename(columns={
            'Date': 'data', 
            'Open': 'abertura', 
            'High': 'maxima', 
            'Low': 'minima', 
            'Volume': 'volume'
        }, inplace=True)
        
        # Cálculo dos Indicadores Técnicos
        df['ema_rapida'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Remove as linhas sem média
        df_final = df.dropna()
        
        if len(df_final) == 0:
            return None
            
        return df_final
    except Exception as e:
        st.sidebar.error(f"Erro técnico ao processar {ticker}: {e}")
        return None

# ==========================================
# 4. INTERFACE PRINCIPAL
# ==========================================
st.title("🏢 Conselheiro B3 - Swing Trade")
st.markdown("Transforme os relatórios do seu Otimizador em ordens precisas na corretora.")
st.markdown("---")

if st.sidebar.button("Analisar Ação", type="primary", use_container_width=True):
    with st.spinner(f"A extrair dados da B3 para {SIMBOLO}..."):
        try:
            df = obter_dados_b3(SIMBOLO)
            
            if df is None:
                st.error("⚠️ Símbolo não encontrado ou sem dados. Esqueceu-se do '.SA' no final? Certifique-se também de que não há espaços em branco no campo de pesquisa.")
            else:
                atual = df.iloc[-1]
                anterior = df.iloc[-2]

                preco = float(atual['fechamento'])

                # Verificações da Estratégia de Pullback
                tendencia_alta = preco > float(atual['sma_50'])
                acao_corrigiu = float(atual['rsi']) < RSI_MAX_ENTRADA
                rompeu_ema9 = preco > float(atual['ema_rapida']) and float(anterior['fechamento']) <= float(anterior['ema_rapida'])

                valor_stop_loss = preco * (1 - STOP_LOSS_PCT)
                valor_alvo_trailing = preco * (1 + TRAILING_STOP_PCT)

                # Lógica de Recomendação Visual
                if tendencia_alta and acao_corrigiu and rompeu_ema9:
                    recomendacao = "🟢 COMPRA IMEDIATA (Gatilho Acionado!)"
                    status = "A ação está em tendência de alta macro, corrigiu bem nos últimos dias e retomou a força hoje."
                    alerta = st.success
                elif tendencia_alta and acao_corrigiu and not rompeu_ema9:
                    recomendacao = "👀 PREPARAR COMPRA (Aguardar Gatilho)"
                    status = "A ação está muito barata (Desconto), mas ainda a cair. Aguarde o fecho do dia acima da EMA 9."
                    alerta = st.info
                elif tendencia_alta and not acao_corrigiu:
                    recomendacao = "⏳ MANTER / NÃO COMPRAR MAIS (Esticada)"
                    status = "A ação já subiu bastante recentemente. Deixe o seu Trailing Stop fluir. Não compre novos lotes aqui."
                    alerta = st.warning
                else:
                    recomendacao = "🔴 FORA DO MERCADO (Tendência de Baixa)"
                    status = "A maré está contra. A ação está a ser negociada abaixo da sua média principal de 50 dias."
                    alerta = st.error

                # Renderizar resultados no ecrã
                st.subheader(recomendacao)
                alerta(status)

                st.markdown("### 📊 Radiografia do Ativo")
                col1, col2, col3 = st.columns(3)
                col1.metric("Preço Atual", f"R$ {preco:.2f}")
                col2.metric("Média Macro (50)", f"R$ {atual['sma_50']:.2f}", "Alta" if preco > atual['sma_50'] else "-Baixa")
                col3.metric(f"RSI (Max {RSI_MAX_ENTRADA})", f"{atual['rsi']:.1f}", "Promoção" if atual['rsi'] < RSI_MAX_ENTRADA else "-Caro")

                # Exibe as ferramentas de gestão de risco se a tendência for favorável
                if "COMPRA" in recomendacao:
                    st.markdown("### 🛡️ Ordens de Proteção na Corretora")
                    st.info("Insira estes valores no seu Home Broker para proteger o capital.")
                    col4, col5 = st.columns(2)
                    col4.metric(f"Preço do Stop Loss (-{STOP_LOSS_PCT*100:.0f}%)", f"R$ {valor_stop_loss:.2f}")
                    col5.metric(f"Alvo Base (Trailing +{TRAILING_STOP_PCT*100:.0f}%)", f"R$ {valor_alvo_trailing:.2f}")

                st.caption(f"Dados atualizados com o último fecho do mercado. ({datetime.now().strftime('%d/%m %H:%M')})")

        except Exception as e:
            st.error(f"Ocorreu um erro inesperado no cálculo. Detalhes: {e}")
else:
    st.write("👈 Insira o código da ação no menu lateral, ajuste os parâmetros do gabarito e clique em **Analisar Ação**.")
