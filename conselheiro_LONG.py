import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Gestor de Posição", layout="wide")

def resgate_coingecko(ticker):
    """Resgate para tokens que o Yahoo não encontra (como o ZBT)"""
    ticker_map = {"ZBT": "zerobase", "ZBT1": "zerobase", "RLS": "reals-network"}
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
st.sidebar.header("⚙️ Parâmetros de Risco")
ticker_input = st.sidebar.text_input("Ativo (ZBT, SOL, PETR4, RLS)", "RLS")
stop_loss_desejado = st.sidebar.number_input("Stop Loss desejado (%)", value=5.0)

st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 ANALISAR AGORA")

# --- Lógica Principal ---
st.title("🏢 Conselheiro Pro: Gestor de Posição")
st.divider()

if btn_analisar:
    with st.spinner(f'Consultando mercado para {ticker_input}...'):
        df, fonte = buscar_dados_perfeitos(ticker_input)
    
    if df is not None:
        # Cálculos de Preço e Volume
        preco_atual = float(df['Close'].iloc[-1])
        volume_atual = float(df['Volume'].iloc[-1])
        volume_medio = float(df['Volume'].mean())
        rsi_valor = float(calcular_rsi(df))
        
        # Média de 50 dias (A tua regra principal)
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_atual = float(df['SMA50'].iloc[-1])
        
        # Estatísticas de Ciclo
        max_180d = float(df['High'].max())
        
        # --- DASHBOARD SUPERIOR ---
        col_m1, col_m2, col_m3 = st.columns(3)
        simbolo_moeda = "$" if "-USD" in fonte or "CoinGecko" in fonte else "R$"
        col_m1.metric("Preço Atual", f"{simbolo_moeda} {preco_atual:.4f}")
        col_m2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col_m3.metric("SMA 50", f"{simbolo_moeda} {sma50_atual:.4f}")
        
        st.divider()
        
        # --- ANÁLISE DE TENDÊNCIA E SEGURANÇA (O NOVO AJUSTE) ---
        st.subheader("🛡️ Verificação de Entrada")
        
        if preco_atual > sma50_atual:
            if rsi_valor > 65:
                # Caso do RLS: Tendência é alta, mas RSI está perigoso
                st.warning(f"⚠️ **TENDÊNCIA DE ALTA, MAS ALERTA:** O preço está acima da SMA 50, mas o RSI ({rsi_valor:.1f}) indica que o ativo está muito esticado (sobrecomprado). **Risco de correção alto. Aguarde um recuo antes de entrar.**")
            else:
                # Cenário ideal: Tendência alta e RSI saudável
                st.success(f"🟢 **SINAL VERDE COMPLETO:** Preço acima da SMA 50 e RSI saudável ({rsi_valor:.1f}). Tendência confirmada.")
        else:
            # Tendência de Baixa
            st.error(f"🔴 **TENDÊNCIA DE BAIXA:** O preço está abaixo da Média de 50 dias ({sma50_atual:.4f}). Não é recomendada a entrada.")
            
        st.divider()
        
        # --- GESTÃO DE SAÍDA ---
        st.subheader("💔 Gestão de Saída / Alvos")
        valor_stop = preco_atual * (1 - (stop_loss_desejado / 100))
        alvo_sugerido = preco_atual * 1.20 # Alvo de 20%
        
        col_s1, col_s2 = st.columns(2)
        col_s1.error(f"Stop Loss Sugerido: {simbolo_moeda} {valor_stop:.4f}")
        col_s2.success(f"Alvo Sugerido (+20%): {simbolo_moeda} {alvo_sugerido:.4f}")
        
        distancia_topo = ((max_180d - preco_atual) / max_180d) * 100
        st.info(f"**Análise de Ciclo:** O preço atual está a **{distancia_topo:.1f}%** abaixo da máxima de 180 dias.")
        st.caption(f"Fonte de dados processada: {fonte}")
    else:
        st.error(f"Erro: Não foi possível encontrar dados para '{ticker_input}'.")
