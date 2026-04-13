import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# 1. Configuração da página
st.set_page_config(page_title="Conselheiro Híbrido OKX/B3", layout="wide")

def buscar_dados_okx(ticker_raw):
    """Busca dados na OKX de forma direta"""
    try:
        # Limpa e formata para o padrão da OKX
        simbolo = ticker_raw.upper().replace("-USD", "").replace("-USDT", "").replace(".SA", "").strip()
        instId = f"{simbolo}-USDT"

        # URLs da OKX (Mercado à Vista)
        url_t = f"https://www.okx.com/api/v5/market/ticker?instId={instId}"
        res_t = requests.get(url_t, timeout=10).json()

        if res_t.get('code') == '0' and len(res_t.get('data', [])) > 0:
            t_data = res_t['data'][0]
            
            # Busca Candles para Máximas e RSI
            url_c = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=1D&limit=180"
            res_c = requests.get(url_c, timeout=10).json()
            
            rsi_valor = 50.0 # Padrão caso falhe o cálculo
            max_180 = float(t_data['last'])
            max_90 = float(t_data['last'])

            if res_c.get('code') == '0' and len(res_c.get('data', [])) > 0:
                df = pd.DataFrame(res_c['data'], columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'confirm'])
                df[['h', 'l', 'c']] = df[['h', 'l', 'c']].apply(pd.to_numeric)
                max_180 = df['h'].max()
                max_90 = df['h'].head(90).max()
                
                # RSI Simples
                delta = df['c'].diff(-1)
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss.replace(0, 0.001)
                rsi_valor = 100 - (100 / (1 + rs.iloc[0]))

            return {
                "preco": float(t_data['last']),
                "max_180d": max_180,
                "max_90d": max_90,
                "rsi": rsi_valor,
                "par": instId,
                "fonte": "OKX"
            }
    except:
        return None
    return None

# --- Interface Lateral ---
st.sidebar.header("⚙️ Configurações")
ticker_input = st.sidebar.text_input("Ativo (Ex: OFC, AVAX, VALE3.SA)", "AVAX").strip()

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?")
preco_compra = st.sidebar.number_input("Preço de Compra ($)", format="%.4f", value=0.0)
stop_loss_pct = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_analisar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_analisar:
    with st.spinner('Buscando dados...'):
        # TENTA OKX PRIMEIRO
        dados = buscar_dados_okx(ticker_input)
        
        # TENTA YAHOO SE FALHAR OU SE FOR .SA
        if not dados:
            try:
                # Se não tem .SA e falhou na OKX, tenta adicionar -USD para o Yahoo
                yf_ticker = ticker_input.upper() if ".SA" in ticker_input.upper() else f"{ticker_input.upper()}-USD"
                yf_df = yf.download(yf_ticker, period='180d', progress=False, auto_adjust=True)
                
                if not yf_df.empty:
                    if isinstance(yf_df.columns, pd.MultiIndex): yf_df.columns = yf_df.columns.get_level_values(0)
                    preco_at = float(yf_df['Close'].iloc[-1])
                    dados = {
                        "preco": preco_at,
                        "max_180d": float(yf_df['High'].max()),
                        "max_90d": float(yf_df['High'].tail(90).max()),
                        "rsi": 50.0,
                        "par": yf_ticker,
                        "fonte": "Yahoo Finance"
                    }
            except: pass

    if dados:
        c1, c2, c3 = st.columns(3)
        c1.metric("Preço Atual", f"$ {dados['preco']:.4f}")
        c2.metric("RSI (14d)", f"{dados['rsi']:.1f}")
        c3.metric("Fonte", f"{dados['par']} ({dados['fonte']})")

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
        st.success(f"Alvo Sugerido (+20%): $ {dados['preco'] * 1.20:.4f}")
    else:
        st.error(f"Erro: Não encontramos dados para '{ticker_input}'. Verifique o nome na corretora.")
