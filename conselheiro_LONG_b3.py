import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# Configuração da página
st.set_page_config(page_title="Conselheiro Crypto OKX", layout="wide")

def buscar_dados_okx(ticker):
    """Busca dados diretamente da API pública da OKX (sem necessidade de chave)"""
    try:
        # A OKX usa o formato 'OFC-USDT' ou 'BTC-USDT'
        instId = ticker.upper().replace("-USD", "-USDT")
        if "-" not in instId:
            instId = f"{instId}-USDT"

        # 1. Busca Ticker (Preço atual e Volume)
        url_ticker = f"https://www.okx.com/api/v5/market/ticker?instId={instId}"
        res_t = requests.get(url_ticker).json()
        
        # 2. Busca Candles (Máximas de 90 e 180 dias)
        # bar=1D (diário), limit=180
        url_candles = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=1D&limit=180"
        res_c = requests.get(url_candles).json()

        if res_t['code'] == '0' and res_c['code'] == '0':
            t_data = res_t['data'][0]
            c_data = res_c['data'] # Lista de candles
            
            df = pd.DataFrame(c_data, columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'confirm'])
            df[['h', 'c', 'vol']] = df[['h', 'c', 'vol']].apply(pd.to_numeric)
            
            return {
                "preco_atual": float(t_data['last']),
                "volume_24h": float(t_data['vol24h']),
                "max_180d": df['h'].max(),
                "max_90d": df['h'].head(90).max(),
                "fonte": "OKX"
            }
    except:
        return None
    return None

# --- Interface Lateral ---
st.sidebar.header("⚙️ Configurações (OKX/B3)")
ticker_input = st.sidebar.text_input("Ativo (ex: OFC, BTC ou VALE3.SA)", "OFC").strip()

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?")
preco_analista = st.sidebar.number_input("Meu Preço de Compra ($)", format="%.4f", value=0.0)
stop_loss_pct = st.sidebar.number_input("Stop Loss desejado (%)", value=5.0)

btn_analisar = st.sidebar.button("🚀 ANALISAR NA FONTE")

# --- Lógica Principal ---
st.title("🚀 Conselheiro Híbrido: OKX & B3")
st.divider()

if btn_analisar:
    with st.spinner(f'Buscando {ticker_input} na OKX...'):
        # Tenta OKX primeiro
        dados = buscar_dados_okx(ticker_input)
        
        # Se falhar na OKX, tenta B3 via Yahoo Finance
        if not dados and ".SA" in ticker_input.upper():
            try:
                yf_data = yf.download(ticker_input, period='180d', progress=False)
                if not yf_data.empty:
                    if isinstance(yf_data.columns, pd.MultiIndex): yf_data.columns = yf_data.columns.get_level_values(0)
                    dados = {
                        "preco_atual": float(yf_data['Close'].iloc[-1]),
                        "volume_24h": float(yf_data['Volume'].iloc[-1]),
                        "max_180d": float(yf_data['High'].max()),
                        "max_90d": float(yf_data['High'].tail(90).max()),
                        "fonte": "Yahoo Finance (B3)"
                    }
            except: pass

    if dados:
        # Dashboard
        c1, c2, c3 = st.columns(3)
        c1.metric("Preço Atual", f"$ {dados['preco_atual']:.4f}")
        c2.metric("Fonte dos Dados", dados['fonte'])
        c3.metric("Máxima 180d", f"$ {dados['max_180d']:.4f}")

        # Performance Pessoal
        if ja_possui and preco_analista > 0:
            st.subheader("💼 Minha Posição")
            lucro_pct = ((dados['preco_atual'] - preco_analista) / preco_analista) * 100
            st.metric("Resultado Atual", f"{lucro_pct:.2f}%", delta=f"{lucro_pct:.2f}%")
        
        # Gestão de Risco
        st.subheader("🛡️ Gestão de Risco")
        v_stop = dados['preco_atual'] * (1 - (stop_loss_pct / 100))
        alvo = dados['preco_atual'] * 1.20
        
        r1, r2 = st.columns(2)
        r1.error(f"Stop Loss Sugerido: $ {v_stop:.4f}")
        r2.success(f"Alvo Sugerido (+20%): $ {alvo:.4f}")
        
        st.info(f"O ativo está a **{((dados['max_180d'] - dados['preco_atual'])/dados['max_180d'])*100:.1f}%** abaixo da máxima de 180 dias.")
    else:
        st.error("Ativo não encontrado na OKX ou B3. Verifique o nome.")
