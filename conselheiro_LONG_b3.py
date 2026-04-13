import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# 1. Configuração da página
st.set_page_config(page_title="Conselheiro Híbrido OKX/B3", layout="wide")

def buscar_dados_okx(ticker):
    """Busca dados na API pública da OKX (Preço, Volume e Máximas)"""
    try:
        # Formata para o padrão OKX (OFC-USDT)
        instId = ticker.upper().replace("-USD", "-USDT")
        if "-" not in instId:
            instId = f"{instId}-USDT"

        # Ticker (Preço e Volume 24h)
        url_t = f"https://www.okx.com/api/v5/market/ticker?instId={instId}"
        # Candles (Máximas e RSI) - Pegamos 180 dias
        url_c = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=1D&limit=180"
        
        res_t = requests.get(url_t).json()
        res_c = requests.get(url_c).json()

        if res_t['code'] == '0' and res_c['code'] == '0' and len(res_c['data']) > 0:
            t_data = res_t['data'][0]
            # Formata Candles para DataFrame
            df = pd.DataFrame(res_c['data'], columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'confirm'])
            df[['h', 'l', 'c', 'vol']] = df[['h', 'l', 'c', 'vol']].apply(pd.to_numeric)
            
            # Cálculo RSI simplificado
            delta = df['c'].diff(-1) # OKX entrega do mais novo para o mais antigo
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
                "fonte": "OKX"
            }
    except: return None
    return None

# --- Barra Lateral ---
st.sidebar.header("⚙️ Configurações de Análise")
ticker_input = st.sidebar.text_input("Ativo (ex: OFC, AVAX ou VALE3.SA)", "OFC").strip()

st.sidebar.divider()
ja_possui = st.sidebar.checkbox("Já possuo este ativo?")
preco_compra = st.sidebar.number_input("Preço de Compra / Analista ($)", format="%.4f", value=0.0)
stop_loss_pct = st.sidebar.number_input("Stop Loss Máximo (%)", value=4.0)

btn_analisar = st.sidebar.button("🚀 ATUALIZAR CONSELHEIRO")

# --- Painel Principal ---
st.title("🚀 Conselheiro Crypto: Gestor de Risco")
st.divider()

if btn_analisar:
    with st.spinner('Sincronizando com as corretoras...'):
        # Tenta OKX (Crypto)
        dados = buscar_dados_okx(ticker_input)
        
        # Se falhar e for B3
        if not dados and ".SA" in ticker_input.upper():
            try:
                yf_df = yf.download(ticker_input, period='180d', progress=False, auto_adjust=True)
                if not yf_df.empty:
                    if isinstance(yf_df.columns, pd.MultiIndex): yf_df.columns = yf_df.columns.get_level_values(0)
                    preco_at = float(yf_df['Close'].iloc[-1])
                    dados = {
                        "preco": preco_at,
                        "vol_24h": float(yf_df['Volume'].iloc[-1]),
                        "max_180d": float(yf_df['High'].max()),
                        "max_90d": float(yf_df['High'].tail(90).max()),
                        "rsi": 50.0, # RSI padrão para B3 nesta versão
                        "fonte": "B3 (Yahoo)"
                    }
            except: pass

    if dados:
        # 1. Dashboard de Métricas
        col1, col2, col3 = st.columns(3)
        col1.metric("Preço Atual", f"$ {dados['preco']:.4f}")
        col2.metric("RSI (14d)", f"{dados['rsi']:.1f}")
        col3.metric("Fonte", dados['fonte'])

        # 2. Minha Posição
        if ja_possui and preco_compra > 0:
            st.subheader("💼 Minha Posição")
            lucro_pct = ((dados['preco'] - preco_compra) / preco_compra) * 100
            st.metric("Resultado Atual", f"{lucro_pct:.2f}%", delta=f"{lucro_pct:.2f}%")
            st.divider()

        # 3. Radiografia de Mercado
        st.subheader("📊 Radiografia de Mercado")
        r1, r2 = st.columns(2)
        r1.info(f"**Máxima 90 dias:** $ {dados['max_90d']:.4f}")
        r2.info(f"**Máxima 180 dias:** $ {dados['max_180d']:.4f}")
        
        dist_topo = ((dados['max_180d'] - dados['preco']) / dados['max_180d']) * 100
        st.write(f"O ativo está a **{dist_topo:.1f}%** abaixo da máxima de 180 dias.")

        # 4. Gestão de Saída
        st.subheader("🛡️ Gestão de Saída")
        v_stop = dados['preco'] * (1 - (stop_loss_pct / 100))
        alvo = dados['preco'] * 1.20 # Alvo de +20%
        
        g1, g2 = st.columns(2)
        g1.error(f"Stop Loss Sugerido: $ {v_stop:.4f}")
        g2.success(f"Alvo Sugerido (+20%): $ {alvo:.4f}")
    else:
        st.error("Erro: Ativo não encontrado. Para Cripto, use a sigla (ex: OFC). Para B3, use .SA (ex: VALE3.SA).")
else:
    st.info("Aguardando entrada de dados na lateral.")
