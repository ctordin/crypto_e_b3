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
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'MBRF3.SA', 'TOTS3.SA',
    'SMTO3.SA', 'ABEV3.SA', 'RENT3.SA', 'SUZB3.SA', 'NATU3.SA', 'ALOS3.SA',
    'MGLU3.SA'
]

# ==========================================
# 2. MOTOR DE ANÁLISE (TÉCNICO + FUNDAMENTOS)
# ==========================================
@st.cache_data(ttl=3600)
def buscar_fundamentos_estavel(ticker_raw):
    """Busca fundamentos no Fundamentus para evitar erros de IP no Yahoo"""
    try:
        # Limpa o ticker (remove .SA) para o padrão brasileiro
        t_limpo = ticker_raw.replace(".SA", "").strip().upper()
        
        import fundamentus
        df_f = fundamentus.get_papel(t_limpo)
        
        if df_f is not None and not df_f.empty:
            return {
                "pl": float(df_f['pl'].iloc[0]) / 100,
                "dy": float(df_f['dy'].iloc[0]) / 100,
                "margem": float(df_f['mrg_liq'].iloc[0]) / 100
            }
    except Exception:
        # Se falhar, o app continua funcionando apenas com a técnica
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
