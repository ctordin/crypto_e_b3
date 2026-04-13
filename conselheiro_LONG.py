import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# 1. Configuração da página
st.set_page_config(page_title="Conselheiro Híbrido Pro", layout="wide")

def buscar_dados_okx(ticker_raw):
    try:
        simbolo = ticker_raw.upper().replace("-USD", "").replace("-USDT", "").strip()
        instId = f"{simbolo}-USDT"
        url_t = f"https://www.okx.com/api/v5/market/ticker?instId={instId}"
        res_t = requests.get(url_t, timeout=5).json()

        if res_t.get('code') == '0' and len(res_t.get('data', [])) > 0:
            t_data = res_t['data'][0]
            url_c = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=1D&limit=180"
            res_c = requests.get(url_c, timeout=5).json()
            
            # Valores padrão
            max_180, rsi_v = float(t_data['last']), 50.0
            if res_c.get('code') == '0' and len(res_c.get('data', [])) > 0:
                df_c = pd.DataFrame(res_c['data'], columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'confirm'])
                max_180 = pd.to_numeric(df_c['h']).max()
                
            return {"preco": float(t_data['last']), "max_180": max_180, "fonte": "OKX"}
    except: return None

# --- Interface Lateral ---
st.sidebar.header("⚙️ Parâmetros")
ticker_input = st.sidebar.text_input("Ativo (Ex: OFC, AVAX, VALE3.SA)", "OFC").strip()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?")
preco_compra = st.sidebar.number_input("Preço de Compra ($)", format="%.4f", value=0.0)
stop_loss_pct = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

# CAMPO DE EMERGÊNCIA: Se as APIs falharem, você digita aqui
st.sidebar.markdown("---")
st.sidebar.subheader("🆘 Entrada Manual (Opcional)")
preco_manual = st.sidebar.number_input("Preço Manual (se erro)", format="%.4f", value=0.0)

btn_analisar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_analisar:
    dados = buscar_dados_okx(ticker_input)
    
    # Plano B: Yahoo Finance
    if not dados:
        try:
            yf_tk = ticker_input.upper() if ".SA" in ticker_input.upper() else f"{ticker_input.upper()}-USD"
            yf_df = yf.download(yf_tk, period='180d', progress=False)
            if not yf_df.empty:
                dados = {"preco": float(yf_df['Close'].iloc[-1]), "max_180": float(yf_df['High'].max()), "fonte": "Yahoo"}
        except: pass

    # Plano C: Entrada Manual do Usuário
    if not dados and preco_manual > 0:
        dados = {"preco": preco_manual, "max_180": preco_manual * 1.10, "fonte": "Manual (Usuário)"}

    if dados:
        col1, col2 = st.columns(2)
        col1.metric("Preço Analisado", f"$ {dados['preco']:.4f}")
        col2.metric("Fonte", dados['fonte'])

        if ja_possui and preco_compra > 0:
            lucro = ((dados['preco'] - preco_compra) / preco_compra) * 100
            st.subheader(f"💼 Resultado Atual: {lucro:.2f}%")

        st.subheader("🛡️ Estratégia de Saída")
        v_stop = dados['preco'] * (1 - (stop_loss_pct / 100))
        v_alvo = dados['preco'] * 1.20
        
        s1, s2 = st.columns(2)
        s1.error(f"STOP LOSS: $ {v_stop:.4f}")
        s2.success(f"ALVO (+20%): $ {v_alvo:.4f}")
        
        st.warning(f"Resistência (Topo 180d): $ {dados['max_180']:.4f}")
    else:
        st.error("Erro total de conexão. Por favor, insira o preço no campo 'Preço Manual' na lateral para calcular.")
