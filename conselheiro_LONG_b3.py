import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
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
        if not inf or len(inf) < 5: 
            return None
        
        pl_valor = inf.get('forwardPE') or inf.get('trailingPE') or inf.get('priceToEarnings') or 0
        dy_valor = (inf.get('dividendYield') or 0) * 100
        margem_valor = (inf.get('profitMargins') or 0) * 100
        
        return {
            "pl": pl_valor,
            "dy": dy_valor,
            "margem": margem_valor
        }
    except:
        return None

@st.cache_data(ttl=300)
def buscar_grafico(ticker):
    try:
        # Aumentado para 250d para garantir dados de 180 dias úteis
        df = yf.download(ticker, period='250d', interval='1d', progress=False)
        if df is None or df.empty: return None
        
        # Ajuste para MultiIndex (evitar erro de Series/Float)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        col_f = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df.rename(columns={col_f: 'fechamento', 'Date': 'data', 'High': 'maxima'}, inplace=True)
        
        # Indicadores Técnicos
        df['ema_9'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (ganho/perda.replace(0, 0.001))))
        
        return df.dropna()
    except: return None

# 3. Interface Lateral
with st.sidebar:
    st.header("⚙️ Parâmetros")
    with st.form("form_gestor"):
        SIMBOLO = st.text_input("Ação (ex: ALOS3.SA)", value="ALOS3.SA").upper().strip()
        
        st.markdown("---")
        POSSUO_ACAO = st.checkbox("Já possuo esta ação?")
        PRECO_COMPRA = st.number_input("Meu Preço de Compra (R$)", value=0.0, step=0.01)
        ALVO_ANALISTA = st.number_input("Alvo do Analista (R$)", value=0.0, step=0.01)
        
        st.markdown("---")
        STOP_LOSS_PCT = st.number_input("Stop Loss desejado (%)", value=5.0) / 100.0
        RSI_MAX = st.number_input("RSI Máx. (Promoção)", value=55)
        
        btn_analisar = st.form_submit_button("🚀 ANALISAR E GERENCIAR", use_container_width=True)

# 4. Painel Principal
st.title("🏢 Conselheiro B3: Gestor de Posição")
st.markdown("---")

if btn_analisar:
    with st.spinner("Sincronizando dados e cálculos de risco..."):
        fund = buscar_fundamentos(SIMBOLO)
        df = buscar_grafico(SIMBOLO)
        
        if df is not None:
            atual = df.iloc[-1]
            preco_atual = float(atual['fechamento'])
            rsi = float(atual['rsi'])
            tend_alta = preco_atual > float(atual['sma_50'])

            # --- NOVO: CÁLCULO DE MÁXIMAS 90 E 180 DIAS ---
            max_180d = float(df['maxima'].tail(180).max())
            max_90d = float(df['maxima'].tail(90).max())

            # BLOCO A: GESTÃO DA SUA CARTEIRA
            if POSSUO_ACAO and PRECO_COMPRA > 0:
                lucro_reais = preco_atual - PRECO_COMPRA
                lucro_pct = (lucro_reais / PRECO_COMPRA) * 100
                
                st.subheader("💰 Minha Posição")
                m1, m2, m3 = st.columns(3)
                m1.metric("Preço Médio", f"R$ {PRECO_COMPRA:.2f}")
                m2.metric("Lucro/Prejuízo", f"R$ {lucro_reais:.2f}", f"{lucro_pct:.2f}%")
                
                if ALVO_ANALISTA > 0:
                    distancia_alvo = ((ALVO_ANALISTA / preco_atual) - 1) * 100
                    m3.metric("Distância do Alvo", f"{distancia_alvo:.1f}%")
                
                st.markdown("---")

            # BLOCO B: FUNDAMENTOS
            if fund:
                st.subheader("📊 Saúde da Empresa")
                f1, f2, f3 = st.columns(3)
                f1.metric("P/L", f"{fund['pl']:.1f}")
                f2.metric("Div. Yield", f"{fund['dy']:.1f}%")
                f3.metric("Margem Líquida", f"{fund['margem']:.1f}%")
                st.markdown("---")

            # --- NOVO BLOCO: RADIOGRAFIA DE TETO (90/180 DIAS) ---
            st.subheader("📉 Resistências e Tetos Recentes")
            c1, c2 = st.columns(2)
            c1.info(f"**Máxima 90 dias:** R$ {max_90d:.2f}")
            c2.info(f"**Máxima 180 dias:** R$ {max_180d:.2f}")
            
            dist_topo = ((max_180d - preco_atual) / max_180d) * 100
            st.write(f"O papel está operando **{dist_topo:.1f}%** abaixo do topo dos últimos 180 dias.")
            st.markdown("---")

            # BLOCO C: MOMENTO TÉCNICO
            st.subheader("📈 Análise de Momento")
            if rsi > 65:
                st.warning(f"⚠️ ATENÇÃO: Ativo esticado (RSI {rsi:.1f}).")
            elif tend_alta and rsi < RSI_MAX:
                st.success("🟢 PONTO DE ENTRADA/APORTE: Ativo em tendência e com desconto.")
            else:
                st.error("🔴 FORA DO SETUP: Tendência de baixa ou risco alto.")

            # BLOCO D: GESTÃO DE RISCO
            st.subheader("🛡️ Gestão de Risco Estrita")
            v_stop = preco_atual * (1 - STOP_LOSS_PCT)
            target = ALVO_ANALISTA if ALVO_ANALISTA > 0 else (preco_atual * 1.10)
            
            r1, r2 = st.columns(2)
            r1.metric("Novo Stop Loss (Sair)", f"R$ {v_stop:.2f}")
            r2.metric("Alvo Estratégico", f"R$ {target:.2f}")

        else:
            st.error("Erro ao carregar dados. Verifique se o ticker termina com .SA (ex: VALE3.SA).")
