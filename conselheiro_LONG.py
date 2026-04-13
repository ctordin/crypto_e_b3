import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# 1. Configuração da página
st.set_page_config(page_title="Conselheiro Híbrido Pro", layout="wide")

def buscar_dados_okx(ticker_raw):
    try:
        # Limpeza robusta do ticker
        simbolo = ticker_raw.upper().replace("-USD", "").replace("-USDT", "").replace(".SA", "").strip()
        instId = f"{simbolo}-USDT"
        
        # Chamada para a API da OKX com cabeçalho de usuário para evitar bloqueios
        headers = {'User-Agent': 'Mozilla/5.0'}
        url_t = f"https://www.okx.com/api/v5/market/ticker?instId={instId}"
        res_t = requests.get(url_t, headers=headers, timeout=10).json()

        if res_t.get('code') == '0' and len(res_t.get('data', [])) > 0:
            t_data = res_t['data'][0]
            
            # Busca histórico para máxima de 180 dias
            url_c = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=1D&limit=180"
            res_c = requests.get(url_c, headers=headers, timeout=10).json()
            
            preco_atual = float(t_data['last'])
            max_180 = preco_atual
            
            if res_c.get('code') == '0' and len(res_c.get('data', [])) > 0:
                df_c = pd.DataFrame(res_c['data'], columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'confirm'])
                max_180 = pd.to_numeric(df_c['h']).max()
                
            return {"preco": preco_atual, "max_180": max_180, "fonte": "OKX Direct"}
    except:
        return None
    return None

# --- Interface Lateral ---
st.sidebar.header("⚙️ Parâmetros")
ticker_input = st.sidebar.text_input("Ativo (Ex: OFC, AVAX, VALE3.SA)", "AVAX").strip()

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?")
preco_compra = st.sidebar.number_input("Preço de Compra ($)", format="%.4f", value=0.0)
stop_loss_pct = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🆘 Entrada Manual (Opcional)")
preco_manual = st.sidebar.number_input("Preço Manual (se erro API)", format="%.4f", value=0.0)

btn_analisar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Painel Principal ---
st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_analisar:
    dados = None
    
    with st.spinner('Sincronizando com o mercado...'):
        # 1. Tenta OKX
        dados = buscar_dados_okx(ticker_input)
        
        # 2. Se falhar, tenta Yahoo Finance
        if not dados:
            try:
                # Ajusta ticker para o Yahoo
                if ".SA" in ticker_input.upper():
                    yf_tk = ticker_input.upper()
                else:
                    yf_tk = f"{ticker_input.upper().replace('-USD', '')}-USD"
                
                yf_df = yf.download(yf_tk, period='180d', progress=False, auto_adjust=True)
                if not yf_df.empty:
                    if isinstance(yf_df.columns, pd.MultiIndex):
                        yf_df.columns = yf_df.columns.get_level_values(0)
                    
                    dados = {
                        "preco": float(yf_df['Close'].iloc[-1]),
                        "max_180": float(yf_df['High'].max()),
                        "fonte": "Yahoo Finance"
                    }
            except:
                pass

    # 3. Se tudo falhar, usa entrada manual
    if not dados and preco_manual > 0:
        dados = {"preco": preco_manual, "max_180": preco_manual * 1.05, "fonte": "Entrada Manual"}

    if dados:
        col1, col2 = st.columns(2)
        col1.metric("Preço Atual", f"$ {dados['preco']:.4f}")
        col2.metric("Fonte", dados['fonte'])

        if ja_possui and preco_compra > 0:
            st.subheader("💼 Minha Posição")
            lucro = ((dados['preco'] - preco_compra) / preco_compra) * 100
            st.metric("Resultado Atual", f"{lucro:.2f}%", delta=f"{lucro:.2f}%")
            st.divider()

        st.subheader("🛡️ Gestão de Saída")
        v_stop = dados['preco'] * (1 - (stop_loss_pct / 100))
        v_alvo = dados['preco'] * 1.20
        
        s1, s2 = st.columns(2)
        s1.error(f"STOP LOSS: $ {v_stop:.4f}")
        s2.success(f"ALVO (+20%): $ {v_alvo:.4f}")
        
        st.info(f"Resistência (Máxima 180d): $ {dados['max_180']:.4f}")
    else:
        st.error("Erro de conexão. Por favor, insira o preço no campo 'Preço Manual' na lateral.")
