import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Gestor de Risco V4", layout="wide")

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
ticker_input = st.sidebar.text_input("Ativo (ZBT, SOL, LINK, PETR4)", "ZBT")
stop_loss_input = st.sidebar.number_input("Stop Loss desejado (%)", value=5.0)

st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 ANALISAR AGORA")

# --- Lógica Principal ---
st.title("🏢 Conselheiro Pro: Gestor de Posição V4")
st.divider()

if btn_analisar:
    with st.spinner(f'Analisando mercado para {ticker_input}...'):
        df, fonte = buscar_dados_perfeitos(ticker_input)
    
    if df is not None:
        # Preço e RSI
        preco_atual = float(df['Close'].iloc[-1])
        rsi_valor = float(calcular_rsi(df))
        
        # Opinião sobre Volume
        volume_atual = float(df['Volume'].iloc[-1])
        volume_medio_20d = float(df['Volume'].rolling(window=20).mean().iloc[-1])
        opiniao_volume = "Alto 📈" if volume_atual > (volume_medio_20d * 1.5) else "Baixo 📉" if volume_atual < (volume_medio_20d * 0.8) else "Normal ↔️"

        # Média de 50 dias e Inclinação
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_atual = float(df['SMA50'].iloc[-1])
        sma50_anterior = float(df['SMA50'].iloc[-3])
        
        # Estatísticas de Máximas (90 e 180 dias)
        max_180d = float(df['High'].max())
        df_90 = df.iloc[-90:] if len(df) >= 90 else df
        max_90d = float(df_90['High'].max())
        
        # Dashboard Superior
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        simbolo = "$" if "-USD" in fonte or "CoinGecko" in fonte else "R$"
        col_m1.metric("Preço Atual", f"{simbolo} {preco_atual:.4f}")
        col_m2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col_m3.metric("Volume (24h)", opiniao_volume)
        col_m4.metric("SMA 50", f"{sma50_atual:.4f}")
        
        st.divider()
        
        # --- VERIFICAÇÃO DE ENTRADA ---
        st.subheader("🛡️ Verificação de Entrada e Tendência")
        if preco_atual > sma50_atual:
            if sma50_atual > sma50_anterior:
                if rsi_valor < 62:
                    st.success(f"🟢 **SINAL VERDE:** Tendência de alta forte. Preço acima da SMA 50 e RSI saudável.")
                else:
                    st.warning(f"⚠️ **ALERTA:** Tendência de alta, mas RSI ({rsi_valor:.1f}) indica sobrecompra.")
            else:
                st.info(f"🟡 **NEUTRO:** Preço acima da média, mas a SMA 50 perdeu inclinação.")
        else:
            st.error(f"🔴 **TENDÊNCIA DE BAIXA:** Fique fora. Preço abaixo da SMA 50.")
            
        st.divider()
        
        # --- GESTÃO DE RISCO E ANÁLISE DE CICLO ---
        st.subheader("📊 Análise de Recuperação e Ciclo")
        
        valor_stop = preco_atual * (1 - (stop_loss_input / 100))
        alvo_sugerido = preco_atual * 1.20
        
        col_s1, col_s2 = st.columns(2)
        col_s1.error(f"Stop Loss Sugerido: {simbolo} {valor_stop:.4f}")
        col_s2.success(f"Alvo Sugerido (+20%): {simbolo} {alvo_sugerido:.4f}")
        
        # Cálculo de Potencial (Restauração da última linha)
        upside_90d = ((max_90d - preco_atual) / preco_atual) * 100
        upside_180d = ((max_180d - preco_atual) / preco_atual) * 100
        
        st.markdown(f"---")
        st.markdown(f"📈 **Potencial de Retorno (Upside):**")
        st.write(f"* Para atingir a máxima de **90 dias** ({simbolo} {max_90d:.4f}), o ativo precisa subir **{upside_90d:.1f}%**.")
        st.write(f"* Para atingir a máxima de **180 dias** ({simbolo} {max_180d:.4f}), o ativo precisa subir **{upside_180d:.1f}%**.")
        
        st.caption(f"Análise baseada em dados de: {fonte}")
    else:
        st.error(f"Erro: Não encontrei dados para '{ticker_input}'.")
