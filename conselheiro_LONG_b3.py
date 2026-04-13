import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro B3 Gestor", page_icon="🏢", layout="centered")

# 2. Funções de Busca
@st.cache_data(ttl=3600)
def buscar_fundamentos(ticker):
    try:
        acao = yf.Ticker(ticker)
        inf = acao.info
        if not inf or len(inf) < 5: return None
        return {
            "pl": inf.get('forwardPE') or inf.get('trailingPE') or 0,
            "dy": (inf.get('dividendYield') or 0) * 100,
            "margem": (inf.get('profitMargins') or 0) * 100
        }
    except: return None

@st.cache_data(ttl=300)
def buscar_dados_mercado(ticker):
    try:
        # Busca 250 dias para garantir o cálculo de 180 dias úteis
        df = yf.download(ticker, period='250d', interval='1d', progress=False, auto_adjust=True)
        if df.empty: return None
        
        # TRATAMENTO DE COLUNAS (Essencial para B3)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.reset_index()
        # Padronização de nomes
        df.rename(columns={'Close': 'fechamento', 'Date': 'data', 'High': 'maxima', 'Volume': 'volume'}, inplace=True)
        
        # Cálculo RSI (14 períodos)
        delta = df['fechamento'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Média Móvel para tendência
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        return df.dropna()
    except: return None

# 3. Interface Lateral
with st.sidebar:
    st.header("⚙️ Parâmetros")
    with st.form("form_gestor"):
        SIMBOLO = st.text_input("Ação (ex: VALE3.SA)", value="ALOS3.SA").upper().strip()
        st.markdown("---")
        POSSUO_ACAO = st.checkbox("Já possuo esta ação?")
        PRECO_COMPRA = st.number_input("Meu Preço de Compra (R$)", value=0.0, step=0.01)
        ALVO_ANALISTA = st.number_input("Alvo do Analista (R$)", value=0.0, step=0.01)
        st.markdown("---")
        STOP_LOSS_PCT = st.number_input("Stop Loss desejado (%)", value=5.0) / 100.0
        RSI_MAX = st.number_input("RSI Máx. (Entrada)", value=55)
        btn_analisar = st.form_submit_button("🚀 ANALISAR AGORA", use_container_width=True)

# 4. Painel Principal
st.title("🏢 Conselheiro B3: Gestor de Posição")
st.divider()

if btn_analisar:
    with st.spinner("Sincronizando dados..."):
        df = buscar_dados_mercado(SIMBOLO)
        fund = buscar_fundamentos(SIMBOLO)
        
        if df is not None:
            # Extração de valores da última linha
            atual = df.iloc[-1]
            preco_atual = float(atual['fechamento'])
            rsi_valor = float(atual['rsi'])
            vol_atual = float(atual['volume'])
            vol_medio = float(df['volume'].tail(20).mean()) # Média dos últimos 20 dias
            
            # Máximas
            max_180d = float(df['maxima'].tail(180).max())
            max_90d = float(df['maxima'].tail(90).max())

            # DASHBOARD DE MÉTRICAS (Preço, RSI, Volume)
            col1, col2, col3 = st.columns(3)
            col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            vol_status = "Alto" if vol_atual > vol_medio else "Baixo"
            col3.metric("Volume", vol_status, help=f"Volume: {vol_atual:,.0f}")

            # BLOCO A: MINHA POSIÇÃO (Se possuir a ação)
            if POSSUO_ACAO and PRECO_COMPRA > 0:
                st.subheader("💰 Minha Posição")
                lucro_reais = preco_atual - PRECO_COMPRA
                lucro_pct = (lucro_reais / PRECO_COMPRA) * 100
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Preço Médio", f"R$ {PRECO_COMPRA:.2f}")
                m2.metric("Resultado", f"{lucro_pct:.2f}%", f"R$ {lucro_reais:.2f}")
                
                if ALVO_ANALISTA > 0:
                    dist_alvo = ((ALVO_ANALISTA / preco_atual) - 1) * 100
                    m3.metric("Até o Alvo", f"{dist_alvo:.1f}%")
                st.divider()

            # BLOCO B: RADIOGRAFIA DE TETO
            st.subheader("📉 Resistências Recentes")
            r1, r2 = st.columns(2)
            r1.info(f"**Máxima 90 dias:** R$ {max_90d:.2f}")
            r2.info(f"**Máxima 180 dias:** R$ {max_180d:.2f}")
            
            # BLOCO C: MOMENTO TÉCNICO
            st.subheader("📈 Análise de Momento")
            tend_alta = preco_atual > float(atual['sma_50'])
            
            if rsi_valor > 70:
                st.warning(f"⚠️ SOBRECOMPRADO: RSI em {rsi_valor:.1f}. Risco de correção alto.")
            elif tend_alta and rsi_valor < RSI_MAX:
                st.success("🟢 COMPRA/APORTE: Tendência de alta com RSI em nível de desconto.")
            elif not tend_alta:
                st.error("🔴 TENDÊNCIA DE BAIXA: Preço abaixo da média de 50 dias.")
            else:
                st.info("🟡 NEUTRO: Aguarde melhor sinal de volume ou RSI.")

            # BLOCO D: GESTÃO DE RISCO
            st.subheader("🛡️ Gestão de Risco")
            v_stop = preco_atual * (1 - STOP_LOSS_PCT)
            alvo_estrate = ALVO_ANALISTA if ALVO_ANALISTA > 0 else (preco_atual * 1.15)
            
            g1, g2 = st.columns(2)
            g1.error(f"Stop Loss Sugerido: R$ {v_stop:.2f}")
            g2.success(f"Alvo Estratégico: R$ {alvo_estrate:.2f}")

        else:
            st.error("Erro ao carregar dados. Verifique o ticker (ex: PETR4.SA).")
else:
    st.info("Configure os parâmetros na lateral e clique em Analisar.")
