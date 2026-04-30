import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configuração da página
st.set_page_config(page_title="Conselheiro Pro: Gestor V6.5", layout="wide")

def resgate_coingecko(ticker):
    # Mapa de IDs para garantir que ativos novos da OKX sejam localizados
    ticker_map = {
        "ZBT": "zerobase", "LINK": "chainlink", "ENJ": "enjincoin", 
        "ORDI": "ordinals", "BIO": "bio-protocol", "MEGA": "mega-token"
    }
    coin_id = ticker_map.get(ticker.upper(), ticker.lower())
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': '180', 'interval': 'daily'}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200: return None
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
    y_ticker = f"{original}-USD" if "-" not in original and "." not in original and not any(char.isdigit() for char in original) else original
    try:
        data = yf.download(y_ticker, period=f"{dias}d", interval="1d", progress=False, auto_adjust=True)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex): 
                data.columns = data.columns.get_level_values(0)
            return data, y_ticker
    except: pass
    data_resgate = resgate_coingecko(original)
    return (data_resgate, f"{original} (via CG)") if data_resgate is not None else (None, original)

def calcular_rsi(data, window=14):
    close = data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 0.001)
    return (100 - (100 / (1 + rs))).iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Parâmetros")
ticker_input = st.sidebar.text_input("Ativo", "LINK")
stop_loss_input = st.sidebar.number_input("Stop Loss (%)", value=5.0)
ref_volume = st.sidebar.selectbox("Média de Volume", options=[1, 5, 20, 30], index=1)

st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 ANALISAR AGORA")

st.title("🏢 Conselheiro Pro: Gestor de Posição V6.5")
st.divider()

if btn_analisar:
    df, fonte = buscar_dados_perfeitos(ticker_input)
    if df is not None:
        # TRAVA DE SEGURANÇA PARA ATIVOS RECENTES (BIO, MEGA, ETC)
        if len(df) < 50:
            st.warning(f"⚠️ **DADOS INSUFICIENTES:** O ativo {ticker_input} é muito recente ({len(df)} dias). O Conselheiro precisa de 50 dias de histórico para calcular a tendência de longo prazo (SMA 50).")
            st.info("Para ativos novos, utilize o gráfico da OKX para análise visual de curto prazo.")
            st.stop()

        preco_atual = float(df['Close'].iloc[-1])
        rsi_valor = float(calcular_rsi(df))
        
        # Lógica de Volume calibrada para OKX (~30% do global)
        fator_okx = 0.30 
        vol_fin_atual = float(df['Volume'].iloc[-1]) * fator_okx
        vol_fin_medio = float(df['Volume'].rolling(window=ref_volume).mean().iloc[-1]) * fator_okx
        
        vol_unidades_atual = vol_fin_atual / preco_atual
        vol_unidades_medio = vol_fin_medio / preco_atual
        vol_gatilho = vol_unidades_medio * 0.9
        
        status_vol = "Alto" if vol_unidades_atual > (vol_unidades_medio * 1.5) else "Baixo" if vol_unidades_atual < vol_gatilho else "Normal"

        df['SMA50'] = df['Close'].rolling(window=50).mean()
        sma50_at = float(df['SMA50'].iloc[-1])
        sma50_ant = float(df['SMA50'].iloc[-3])
        dist_media = ((preco_atual - sma50_at) / sma50_at) * 100
        
        # Dashboard Superior
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Preço Atual", f"$ {preco_atual:.4f}")
        col_m2.metric("RSI (14d)", f"{rsi_valor:.1f}")
        col_m3.metric("Volume (Tokens)", status_vol)
        col_m4.metric("SMA 50", f"{sma50_at:.4f}")
        
        st.divider()
        if status_vol == "Baixo":
            st.warning(f"📌 **GATILHO OKX:** Para sinal VERDE, o 'Vol. 24h' na OKX deve superar **{vol_gatilho:,.0f}** unidades.")
        
        # Verificação de Entrada
        st.subheader("🛡️ Verificação de Entrada")
        if preco_atual > sma50_at:
            if status_vol != "Baixo" and sma50_at > sma50_ant and dist_media > 1.0:
                st.success("🟢 **SINAL VERDE:** Tendência confirmada.")
            elif status_vol == "Baixo":
                st.info("🟡 **AGUARDAR VOLUME:** Preço acima da média, mas falta força compradora.")
            else:
                st.info('🟡 **NEUTRO:** Preço "colado" na média ou tendência lateral.')
        else:
            st.error("🔴 **TENDÊNCIA DE BAIXA:** Ativo operando abaixo da média de 50 dias.")

        st.divider()
        
        # Ciclos e Risco
        st.subheader("📊 Ciclos de Resistência e Risco")
        df_rec = df.iloc[-90:]
        max_90 = float(df_rec['High'].max())
        df_ant = df.iloc[:-90] if len(df) > 90 else None
        max_180 = float(df_ant['High'].max()) if df_ant is not None else max_90
        
        up90 = ((max_90 - preco_atual) / preco_atual) * 100
        up180 = ((max_180 - preco_atual) / preco_atual) * 100
        
        c1, c2 = st.columns(2)
        c1.info(f"Pico 0-90 dias: $ {max_90:.4f} (Upside: {up90:.1f}%)")
        c2.info(f"Pico 90-180 dias: $ {max_180:.4f} (Upside: {up180:.1f}%)")
        
        st.error(f"⚠️ Stop Loss Sugerido: $ {preco_atual * (1 - (stop_loss_input / 100)):.4f}")
        st.caption(f"Análise: {fonte} | Gatilho calibrado para unidades de Token.")
    else:
        st.error(f"Ativo '{ticker_input}' não encontrado.")
