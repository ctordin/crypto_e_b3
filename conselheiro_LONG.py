import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Gestor V6.2", layout="wide")

def resgate_coingecko(ticker):
    ticker_map = {"ZBT": "zerobase", "ZBT1": "zerobase", "RLS": "reals-network", "LINK": "chainlink", "ENJ": "enjincoin"}
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
ticker_input = st.sidebar.text_input("Ativo (ZBT, SOL, LINK, ENJ)", "ENJ")
stop_loss_input = st.sidebar.number_input("Stop Loss desejado (%)", value=5.0)

# Novo Parâmetro de Calibração de Volume
ref_volume = st.sidebar.selectbox(
    "Referência de Volume (Méd. Móvel)",
    options=[1, 5, 20, 30],
    index=1,
    help="Escolha o período da média para comparar o volume atual. 1 para diário, 5 para semanal curto, 30 para mensal."
)

st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 ANALISAR AGORA")

# --- Lógica Principal ---
st.title("🏢 Conselheiro Pro: Gestor de Posição V6.2")
st.divider()

if btn_analisar:
    with st.spinner(f'Analisando mercado para {ticker_input}...'):
        df, fonte = buscar_dados_perfeitos(ticker_input)
    
    if df is not None:
        preco_atual = float(df['Close'].iloc[-1])
        rsi_valor = float(calcular_rsi(df))
        
        # --- Lógica de Volume Calibrada ---
        vol_atual = float(df['Volume'].iloc[-1])
        vol_medio = float(df['Volume'].rolling(window=ref_volume).mean().iloc[-1])
        
        # Gatilho: 90% da média escolhida
        vol_gatilho = vol_medio * 0.9 
        status_vol = "Alto" if vol_atual > (vol_medio * 1.5) else "Baixo" if vol_atual < vol_gatilho else "Normal"

        # SMA 50 e Inclinação
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_at = float(df['SMA50'].iloc[-1])
        sma50_ant = float(df['SMA50'].iloc[-3])
        distancia_media = ((preco_atual - sma50_at) / sma50_at) * 100
        
        # Picos Segmentados
        df_recente = df.iloc[-90:] if len(df) >= 90 else df
        max_0_90 = float(df_recente['High'].max())
        df_antigo = df.iloc[:-90] if len(df) >= 90 else None
        max_90_180 = float(df_antigo['High'].max()) if df_antigo is not None else max_0_90
        
        # Dashboard Superior
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        simbolo = "$" if "-USD" in fonte or "CoinGecko" in fonte else "R$"
        col_m1.metric("Preço Atual", f"{simbolo} {preco_atual:.4f}")
        col_m2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col_m3.metric(f"Vol. vs Méd.{ref_volume}d", f"{status_vol}")
        col_m4.metric("SMA 50", f"{sma50_at:.4f}")
        
        st.divider()
        
        # --- PAINEL DE GATILHO OKX ---
        if status_vol == "Baixo":
            st.warning(f"📌 **GATILHO OKX:** O volume atual é baixo. Para o sinal ficar verde, o '24h Vol' na OKX deve ultrapassar **{vol_gatilho:,.0f}**.")
        
        # --- FILTRO DE ENTRADA V6.2 ---
        st.subheader("🛡️ Verificação de Entrada e Tendência")
        
        if preco_atual > sma50_at:
            if sma50_at > sma50_ant and status_vol != "Baixo" and distancia_media > 1.0:
                if rsi_valor < 62:
                    st.success(f"🟢 **SINAL VERDE:** Tendência confirmada com volume ({status_vol}) e margem.")
                else:
                    st.warning(f"⚠️ **ALERTA:** RSI ({rsi_valor:.1f}) indica sobrecompra.")
            elif status_vol == "Baixo":
                st.info(f"🟡 **AGUARDAR VOLUME:** Preço acima da média, mas sem força. Falta volume comprador.")
            elif distancia_media <= 1.0:
                st.info(f'🟡 **NEUTRO (Margem Curta):** Preço muito próximo à SMA 50.')
            else:
                st.info(f"🟡 **NEUTRO:** SMA 50 perdeu inclinação.")
        else:
            st.error(f"🔴 **TENDÊNCIA DE BAIXA:** Preço abaixo da SMA 50.")

        st.divider()
        
        # Ciclos de Resistência
        st.subheader("📊 Ciclos de Resistência e Risco")
        up_recente = ((max_0_90 - preco_atual) / preco_atual) * 100
        up_antigo = ((max_90_180 - preco_atual) / preco_atual) * 100
        
        c_p1, c_p2 = st.columns(2)
        c_p1.info(f"Pico 0-90 dias: {simbolo} {max_0_90:.4f} (Upside: {up_recente:.1f}%)")
        c_p2.info(f"Pico 90-180 dias: {simbolo} {max_90_180:.4f} (Upside: {up_antigo:.1f}%)")
        
        st.error(f"Stop Loss Sugerido: {simbolo} {preco_atual * (1 - (stop_loss_input / 100)):.4f}")
        st.caption(f"Análise: {fonte} | Méd. Volume {ref_volume}d: {vol_medio:,.0f}")
    else:
        st.error(f"Ativo '{ticker_input}' não encontrado.")
