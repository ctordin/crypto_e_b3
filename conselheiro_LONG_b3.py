import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Conselheiro B3 Resiliente", page_icon="🏢", layout="centered")

st.sidebar.header("⚙️ Parâmetros da Ação")
SIMBOLO = st.sidebar.text_input("Ação (ex: VALE3.SA)", value="VALE3.SA").upper().strip()

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Gestão de Risco")
STOP_LOSS_PCT = st.sidebar.number_input("Stop Loss (%)", min_value=1.0, max_value=15.0, value=5.0) / 100.0
TRAILING_STOP_PCT = st.sidebar.number_input("Trailing Stop (%)", min_value=1.0, max_value=30.0, value=10.0) / 100.0
RSI_MAX_ENTRADA = st.sidebar.number_input("RSI Máx. (Promoção)", min_value=30, max_value=80, value=55)

# ==========================================
# 2. MOTORES DE DADOS (INDEPENDENTES)
# ==========================================
def obter_fundamentos_seguro(ticker):
    try:
        acao = yf.Ticker(ticker)
        inf = acao.info
        if not inf or len(inf) < 5: return None # Verifica se o Yahoo retornou dados reais
        
        return {
            "pl": inf.get('forwardPE') or inf.get('trailingPE') or 0,
            "dy": (inf.get('dividendYield') or 0) * 100,
            "margem": (inf.get('profitMargins') or 0) * 100,
            "saudavel": (inf.get('profitMargins') or 0) > 0.05
        }
    except:
        return None

def obter_grafico_seguro(ticker):
    try:
        df = yf.download(ticker, period='150d', interval='1d', progress=False)
        if df is None or df.empty: return None
        
        # Limpeza de colunas (VALE3 fix)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        df = df.reset_index()
        
        col_fechamento = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df.rename(columns={col_fechamento: 'fechamento', 'Date': 'data'}, inplace=True)
        
        # Cálculo Indicadores
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
# 3. EXECUÇÃO DA INTERFACE
# ==========================================
st.title("🏢 Conselheiro B3")
st.markdown("---")

if st.sidebar.button("Analisar Agora", type="primary", use_container_width=True):
    # Tenta obter dados de forma independente
    fund = obter_fundamentos_seguro(SIMBOLO)
    df = obter_grafico_seguro(SIMBOLO)

    # Bloco 1: Fundamentos (Se houver erro, apenas avisa mas continua)
    if fund:
        st.subheader("📊 Saúde Financeira")
        c1, c2, c3 = st.columns(3)
        c1.metric("P/L", f"{fund['pl']:.1f}")
        c2.metric("Div. Yield", f"{fund['dy']:.1f}%")
        c3.metric("Margem", f"{fund['margem']:.1f}%")
    else:
        st.warning("⚠️ Nota: Não foi possível carregar os fundamentos agora (Yahoo instável). Prosseguindo apenas com análise técnica.")

    # Bloco 2: Gráfico e Stop Loss (O coração da operação)
    if df is not None:
        atual = df.iloc[-1]
        anterior = df.iloc[-2]
        preco = float(atual['fechamento'])
        rsi = float(atual['rsi'])
        
        tendencia_alta = preco > float(atual['sma_50'])
        em_promocao = rsi < RSI_MAX_ENTRADA
        rompeu_ema9 = preco > float(atual['ema_9']) and float(anterior['fechamento']) <= float(anterior['ema_9'])

        # Status do Gatilho
        if tendencia_alta and em_promocao and rompeu_ema9:
            st.success("🚀 **GATILHO DE COMPRA!**")
        elif tendencia_alta and em_promocao:
            st.info("👀 **EM OBSERVAÇÃO** (Aguarde romper EMA 9)")
        elif tendencia_alta and not em_promocao:
            st.warning("⏳ **ESTICADA** (Aguarde recuo)")
        else:
            st.error("🔴 **TENDÊNCIA DE BAIXA**")

        # Métricas Técnicas
        t1, t2, t3 = st.columns(3)
        t1.metric("Preço Atual", f"R$ {preco:.2f}")
        t2.metric("RSI", f"{rsi:.1f}")
        t3.metric("Média 50", "Acima" if tendencia_alta else "Abaixo")

        # Gestão de Risco
        st.markdown("### 🛡️ Ordens para Corretora")
        v_stop = preco * (1 - STOP_LOSS_PCT)
        v_alvo = preco * (1 + TRAILING_STOP_PCT)
        
        r1, r2 = st.columns(2)
        r1.metric("Stop Loss (Sair)", f"R$ {v_stop:.2f}")
        r2.metric("Ativar Trailing", f"R$ {v_alvo:.2f}")
        
        st.caption(f"Dados atualizados em: {datetime.now().strftime('%H:%M:%S')}")
    else:
        st.error(f"❌ Erro Crítico: Não consegui baixar os preços de {SIMBOLO}. Verifique sua conexão ou se o ticker está correto.")
else:
    st.write("Aguardando análise...")
