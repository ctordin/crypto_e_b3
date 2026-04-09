import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 1. Configuração da Página
st.set_page_config(page_title="Conselheiro B3 Completo", page_icon="🏢", layout="centered")

# 2. Motores de Busca com Cache
@st.cache_data(ttl=3600)
def buscar_fundamentos(ticker):
    try:
        acao = yf.Ticker(ticker)
        inf = acao.info
        if not inf or len(inf) < 10: return None
        return {
            "pl": inf.get('forwardPE') or inf.get('trailingPE') or 0,
            "dy": (inf.get('dividendYield') or 0) * 100,
            "margem": (inf.get('profitMargins') or 0) * 100
        }
    except:
        return None

@st.cache_data(ttl=300)
def buscar_grafico(ticker):
    try:
        df = yf.download(ticker, period='150d', interval='1d', progress=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        df = df.reset_index()
        col_f = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df.rename(columns={col_f: 'fechamento', 'Date': 'data'}, inplace=True)
        
        df['ema_9'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (ganho/perda)))
        return df.dropna()
    except:
        return None

# 3. Interface Lateral (Formulário para não travar)
with st.sidebar:
    st.header("⚙️ Configurações")
    with st.form("form_analise"):
        SIMBOLO = st.text_input("Ação (ex: PETR4.SA)", value="").upper().strip()
        st.markdown("---")
        STOP_LOSS_PCT = st.number_input("Stop Loss (%)", value=5.0) / 100.0
        TRAILING_STOP_PCT = st.number_input("Trailing Stop (%)", value=10.0) / 100.0
        RSI_MAX = st.number_input("RSI Máx.", value=55)
        btn_analisar = st.form_submit_button("🚀 ANALISAR AGORA", use_container_width=True)

# 4. Painel de Resultados
st.title("🏢 Conselheiro B3 Quantamental")
st.markdown("---")

if btn_analisar:
    if not SIMBOLO:
        st.warning("⚠️ Digite o código da ação.")
    else:
        with st.spinner("Processando análise técnica e fundamentalista..."):
            fund = buscar_fundamentos(SIMBOLO)
            df = buscar_grafico(SIMBOLO)
            
            if df is not None:
                atual = df.iloc[-1]
                anterior = df.iloc[-2]
                preco = float(atual['fechamento'])
                rsi = float(atual['rsi'])
                
                # Bloco Fundamentalista (Se disponível)
                if fund:
                    st.subheader("📊 Radiografia Fundamentalista")
                    f1, f2, f3 = st.columns(3)
                    f1.metric("P/L", f"{fund['pl']:.1f}")
                    f2.metric("Dividend Yield", f"{fund['dy']:.1f}%")
                    f3.metric("Margem Líquida", f"{fund['margem']:.1f}%")
                    st.markdown("---")
                
                # Lógica e Decisão Técnica
                tend_alta = preco > float(atual['sma_50'])
                rompeu_ema9 = preco > float(atual['ema_9']) and float(anterior['fechamento']) <= float(anterior['ema_9'])

                st.subheader("📈 Análise de Momento")
                if tend_alta and rsi < RSI_MAX and rompeu_ema9:
                    st.success("🟢 GATILHO DE COMPRA: Setup completo identificado!")
                elif tend_alta and rsi < RSI_MAX:
                    st.info("🟡 EM OBSERVAÇÃO: Tendência e Preço OK, aguardando virada da EMA 9.")
                else:
                    st.error("🔴 FORA DO SETUP: Ativo esticado ou em tendência macro de baixa.")

                t1, t2, t3 = st.columns(3)
                t1.metric("Preço Atual", f"R$ {preco:.2f}")
                t2.metric("RSI", f"{rsi:.1f}")
                t3.metric("Acima da Média 50", "Sim" if tend_alta else "Não")

                # Gestão de Risco
                st.subheader("🛡️ Gestão de Risco")
                v_stop = preco * (1 - STOP_LOSS_PCT)
                v_alvo = preco * (1 + TRAILING_STOP_PCT)
                
                r1, r2 = st.columns(2)
                r1.metric("Stop Loss (Sair)", f"R$ {v_stop:.2f}")
                r2.metric("Alvo Trailing", f"R$ {v_alvo:.2f}")
            else:
                st.error("❌ Erro ao baixar dados. Verifique o ticker (ex: VALE3.SA).")
else:
    st.info("Utilize o formulário à esquerda para iniciar a análise.")
