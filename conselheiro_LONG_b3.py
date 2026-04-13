import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# 1. Configuração da página
st.set_page_config(page_title="Conselheiro Híbrido OKX/B3", layout="wide")

def buscar_dados_okx(ticker):
    """Busca dados na API pública da OKX com tratamento de nome"""
    try:
        # TRATAMENTO DO NOME: Remove -USD ou -USDT e remonta para o padrão OKX
        simbolo = ticker.upper().replace("-USD", "").replace("-USDT", "").strip()
        instId = f"{simbolo}-USDT"

        # URLs da OKX
        url_t = f"https://www.okx.com/api/v5/market/ticker?instId={instId}"
        url_c = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=1D&limit=180"
        
        res_t = requests.get(url_t).json()
        res_c = requests.get(url_c).json()

        if res_t['code'] == '0' and len(res_t['data']) > 0:
            t_data = res_t['data'][0]
            
            # Processa Candles para Máximas e RSI
            if res_c['code'] == '0' and len(res_c['data']) > 0:
                df = pd.DataFrame(res_c['data'], columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'confirm'])
                df[['h', 'l', 'c', 'vol']] = df[['h', 'l', 'c', 'vol']].apply(pd.to_numeric)
                
                # RSI (Calculado sobre os candles da OKX)
                delta = df['c'].diff(-1)
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss.replace(0, 0.001)
                rsi_valor = 100 - (100 / (1 + rs.iloc[0]))

                return {
                    "preco": float(t_data['last']),
                    "vol_24h": float(t_data['vol24h']),
                    "max_180d": df['h'].max(),
                    "max_90d": df['h'].head(90).max(),
                    "rsi": rsi_valor,
                    "fonte": "OKX Direct"
                }
    except Exception as e:
        return None
    return None

# --- Restante do código (Barra Lateral e Interface) ---
st.sidebar.header("⚙️ Configurações de Análise")
# Sugestão: deixe apenas 'OFC' para testar
ticker_input = st.sidebar.text_input("Ativo (ex: OFC, AVAX ou VALE3.SA)", "OFC").strip()

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?")
preco_compra = st.sidebar.number_input("Preço de Compra / Analista ($)", format="%.4f", value=0.0)
stop_loss_pct = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_analisar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_analisar:
    dados = buscar_dados_okx(ticker_input)
    
    # Se não achar na OKX e tiver .SA, tenta Yahoo
    if not dados and ".SA" in ticker_input.upper():
        # (Lógica do Yahoo Finance que já estava no código anterior)
        try:
            yf_df = yf.download(ticker_input, period='180d', progress=False, auto_adjust=True)
            if not yf_df.empty:
                if isinstance(yf_df.columns, pd.MultiIndex): yf_df.columns = yf_df.columns.get_level_values(0)
                dados = {
                    "preco": float(yf_df['Close'].iloc[-1]),
                    "vol_24h": float(yf_df['Volume'].iloc[-1]),
                    "max_180d": float(yf_df['High'].max()),
                    "max_90d": float(yf_df['High'].tail(90).max()),
                    "rsi": 50.0,
                    "fonte": "B3 (Yahoo)"
                }
        except: pass

    if dados:
        col1, col2, col3 = st.columns(3)
        col1.metric("Preço Atual", f"$ {dados['preco']:.4f}")
        col2.metric("RSI (14d)", f"{dados['rsi']:.1f}")
        col3.metric("Fonte", dados['fonte'])

        if ja_possui and preco_compra > 0:
            st.subheader("💼 Minha Posição")
            lucro = ((dados['preco'] - preco_compra) / preco_compra) * 100
            st.metric("Resultado", f"{lucro:.2f}%", delta=f"{lucro:.2f}%")

        st.subheader("📊 Radiografia de Mercado")
        r1, r2 = st.columns(2)
        r1.info(f"**Máxima 90 dias:** $ {dados['max_90d']:.4f}")
        r2.info(f"**Máxima 180 dias:** $ {dados['max_180d']:.4f}")

        st.subheader("🛡️ Gestão de Saída")
        v_stop = dados['preco'] * (1 - (stop_loss_pct / 100))
        st.error(f"Stop Loss Sugerido: $ {v_stop:.4f}")
    else:
        st.error("Ativo não encontrado. Tente apenas 'OFC' sem o '-USD'.")
