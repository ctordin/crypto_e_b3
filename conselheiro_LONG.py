import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Gestor de Risco", layout="wide")

def resgate_coingecko(ticker):
    """Resgate para tokens que o Yahoo não encontra (ZBT, RLS, LINK)"""
    ticker_map = {"ZBT": "zerobase", "ZBT1": "zerobase", "RLS": "reals-network", "LINK": "chainlink"}
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
ticker_input = st.sidebar.text_input("Ativo (ZBT, SOL, LINK, PETR4)", "LINK")
stop_loss_input = st.sidebar.number_input("Stop Loss desejado (%)", value=5.0)

st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 ANALISAR AGORA")

# --- Lógica Principal ---
st.title("🏢 Conselheiro Pro: Gestor de Posição V2")
st.divider()

if btn_analisar:
    with st.spinner(f'Analisando mercado para {ticker_input}...'):
        df, fonte = buscar_dados_perfeitos(ticker_input)
    
    if df is not None:
        # Preço e Volume
        preco_atual = float(df['Close'].iloc[-1])
        rsi_valor = float(calcular_rsi(df))
        
        # Média de 50 dias e Inclinação (Slope)
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_atual = float(df['SMA50'].iloc[-1])
        sma50_anterior = float(df['SMA50'].iloc[-3]) # Média de 3 dias atrás para ver a direção
        
        # Dashboard Superior
        col_m1, col_m2, col_m3 = st.columns(3)
        simbolo = "$" if "-USD" in fonte or "CoinGecko" in fonte else "R$"
        col_m1.metric("Preço Atual", f"{simbolo} {preco_atual:.4f}")
        col_m2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col_m3.metric("Média 50d", f"{preco_atual:.4f}")
        
        st.divider()
        
        # --- FILTRO DE ENTRADA INTELIGENTE (O AJUSTE DA LINK) ---
        st.subheader("🛡️ Verificação de Entrada e Tendência")
        
        if preco_atual > sma50_atual:
            # Filtro 1: A média está subindo? (Evita topos arredondados)
            if sma50_atual > sma50_anterior:
                # Filtro 2: O RSI está saudável? (Evita compras esticadas)
                if rsi_valor < 62:
                    st.success(f"🟢 **COMPRA CONFIRMADA:** O preço está acima da SMA 50, a média está subindo e o RSI ({rsi_valor:.1f}) permite entrada.")
                else:
                    st.warning(f"⚠️ **AGUARDAR:** Tendência de alta confirmada, mas o RSI ({rsi_valor:.1f}) indica sobrecompra. Risco de queda iminente.")
            else:
                # Caso da LINK hoje cedo: Preço acima, mas média perdendo força
                st.info(f"🟡 **NEUTRO / CUIDADO:** Preço acima da SMA 50, mas a média parou de subir. O momentum está fraco. Risco de 'falso rompimento'.")
        else:
            st.error(f"🔴 **TENDÊNCIA DE BAIXA:** Preço abaixo da SMA 50 ({sma50_atual:.4f}). Fique fora deste ativo.")
            
        st.divider()
        
        # --- GESTÃO DE RISCO ---
        st.subheader("💔 Gestão de Saída")
        valor_stop = preco_atual * (1 - (stop_loss_input / 100))
        alvo_sugerido = preco_atual * 1.20
        
        col_s1, col_s2 = st.columns(2)
        col_s1.error(f"Stop Loss Sugerido: {simbolo} {valor_stop:.4f}")
        col_s2.success(f"Alvo Sugerido (+20%): {simbolo} {alvo_sugerido:.4f}")
        
        st.caption(f"Análise baseada em dados de: {fonte}")
    else:
        st.error(f"Erro: Não encontrei dados para '{ticker_input}'.")
