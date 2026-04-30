import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Gestor V6.3", layout="wide")

def resgate_coingecko(ticker):
    ticker_map = {"ZBT": "zerobase", "ZBT1": "zerobase", "RLS": "reals-network", "LINK": "chainlink", "ENJ": "enjincoin", "ORDI": "ordinals"}
    coin_id = ticker_map.get(ticker.upper(), ticker.lower())
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': '180', 'interval': 'daily'}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'Close'])
        df['Volume'] = [v[1] for v in data['total_volumes']]
        df['High'] = df['Close']
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except:
        return None

def buscar_dados_perfeitos(ticker, dias=180):
    original = ticker.upper().strip()
    y_ticker = original
    if "-" not in y_ticker and "." not in y_ticker:
        if not any(char.isdigit() for char in y_ticker):
            y_ticker = f"{y_ticker}-USD"
        else:
            y_ticker = f"{y_ticker}.SA"
            
    try:
        data = yf.download(y_ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data, y_ticker
    except:
        pass
    
    data_resgate = resgate_coingecko(original)
    if data_resgate is not None:
        return data_resgate, f"{original} (via CoinGecko)"
    return None, original

def calcular_rsi(data, window=14):
    close = data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 0.001)
    return (100 - (100 / (1 + rs))).iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Parâmetros de Entrada")
ticker_input = st.sidebar.text_input("Ativo (ORDI, ENJ, LINK)", "ORDI")
stop_loss_input = st.sidebar.number_input("Stop Loss desejado (%)", value=5.0)

ref_volume = st.sidebar.selectbox(
    "Referência de Volume (Méd. Móvel)",
    options=[1, 5, 20, 30],
    index=1
)

st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 ANALISAR AGORA")

# --- Lógica Principal ---
st.title("🏢 Conselheiro Pro: Gestor de Posição V6.3")
st.divider()

if btn_analisar:
    with st.spinner(f'Analisando mercado para {ticker_input}...'):
        df, fonte = buscar_dados_perfeitos(ticker_input)
    
    if df is not None:
        preco_atual = float(df['Close'].iloc[-1])
        rsi_valor = float(calcular_rsi(df))
        
        # --- LÓGICA DE CONVERSÃO PARA UNIDADES (OKX STYLE) ---
        vol_financeiro_atual = float(df['Volume'].iloc[-1])
        vol_financeiro_medio = float(df['Volume'].rolling(window=ref_volume).mean().iloc[-1])
        
        # Convertendo Dólares para Quantidade de Tokens (Preço Médio do dia)
        vol_tokens_atual = vol_financeiro_atual / preco_atual
        vol_tokens_medio = vol_financeiro_medio / preco_atual
        
        # Gatilho em Unidades de Token
        vol_gatilho_unidades = vol_tokens_medio * 0.9 
        status_vol = "Alto" if vol_tokens_atual > (vol_tokens_medio * 1.5) else "Baixo" if vol_tokens_atual < vol_gatilho_unidades else "Normal"

        # Média e Picos
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_at = float(df['SMA50'].iloc[-1])
        distancia_media = ((preco_atual - sma50_at) / sma50_at) * 100
        
        # Dashboard Superior
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        simbolo = "$" if "-USD" in fonte or "CoinGecko" in fonte else "R$"
        col_m1.metric("Preço Atual", f"{simbolo} {preco_atual:.4f}")
        col_m2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col_m3.metric(f"Vol. em Unidades", f"{status_vol}")
        col_m4.metric("SMA 50", f"{sma50_at:.4f}")
        
        st.divider()
        
        # --- PAINEL DE GATILHO EM UNIDADES (Sincronizado com OKX) ---
        if status_vol == "Baixo":
            st.warning(f"📌 **GATILHO OKX:** O volume em tokens é baixo. Para o sinal ficar verde, o 'Vol. 24h ({ticker_input.upper()})' na OKX deve ultrapassar **{vol_gatilho_unidades:,.0f}** unidades.")
        
        # Verificação de Tendência
        if preco_atual > sma50_at:
            if status_vol != "Baixo" and distancia_media > 1.0:
                st.success(f"🟢 **SINAL VERDE:** Tendência confirmada com volume em unidades e margem.")
            elif status_vol == "Baixo":
                st.info(f"🟡 **AGUARDAR VOLUME:** Volume de tokens abaixo da média de {ref_volume} dias.")
            else:
                st.info(f"🟡 **NEUTRO:** Sem margem de segurança na SMA 50.")
        else:
            st.error(f"🔴 **TENDÊNCIA DE BAIXA:** Fique fora.")

        st.divider()
        st.caption(f"Análise: {fonte} | Média de Vol. ({ref_volume}d) em Unidades: {vol_tokens_medio:,.0f}")
    else:
        st.error(f"Ativo '{ticker_input}' não encontrado.")
