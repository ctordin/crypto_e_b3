import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conselheiro B3: Gestor V6.5", layout="wide")

def calcular_rsi(data, window=14):
    close = data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 0.001)
    return (100 - (100 / (1 + rs))).iloc[-1]

# --- Interface Lateral ---
st.sidebar.header("⚙️ Parâmetros B3")
ticker_input = st.sidebar.text_input("Ação (ex: VALE3, PETR4)", "B3SA3")
stop_loss_input = st.sidebar.number_input("Stop Loss desejado (%)", value=5.0)
ref_volume = st.sidebar.selectbox("Média de Volume (Dias)", options=[1, 5, 20, 30], index=1)

st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 ANALISAR AGORA")

st.title("🏢 Conselheiro B3: Gestor de Posição V6.5")
st.divider()

if btn_analisar:
    # Garante o sufixo .SA para a B3
    ticker_final = ticker_input.upper().strip()
    if ".SA" not in ticker_final:
        ticker_final = f"{ticker_final}.SA"
    
    try:
        df = yf.download(ticker_final, period="180d", interval="1d", progress=False, auto_adjust=True)
        
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            preco_atual = float(df['Close'].iloc[-1])
            rsi_valor = float(calcular_rsi(df))
            
            # Lógica de Volume (Comparação Direta com a Média)
            vol_atual = float(df['Volume'].iloc[-1])
            vol_medio = float(df['Volume'].rolling(window=ref_volume).mean().iloc[-1])
            vol_gatilho = vol_medio * 0.9
            
            status_vol = "Alto" if vol_atual > (vol_medio * 1.5) else "Baixo" if vol_atual < vol_gatilho else "Normal"

            df['SMA50'] = df['Close'].rolling(window=50).mean()
            sma50_at = float(df['SMA50'].iloc[-1])
            sma50_ant = float(df['SMA50'].iloc[-3])
            dist_media = ((preco_atual - sma50_at) / sma50_at) * 100
            
            # Dashboard Superior (Igual ao Crypto)
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            col_m2.metric("RSI (14d)", f"{rsi_valor:.1f}")
            col_m3.metric(f"Vol. vs Méd.{ref_volume}d", status_vol)
            col_m4.metric("SMA 50", f"R$ {sma50_at:.2f}")
            
            st.divider()
            
            if status_vol == "Baixo":
                st.warning(f"📌 **GATILHO DE VOLUME:** O volume atual está abaixo da média. Para sinal VERDE, o volume diário deve superar **{vol_gatilho:,.0f}**.")

            # Verificação de Entrada
            st.subheader("🛡️ Verificação de Entrada")
            if preco_atual > sma50_at:
                if status_vol != "Baixo" and sma50_at > sma50_ant and dist_media > 1.0:
                    st.success("🟢 **SINAL VERDE:** Tendência de alta confirmada com volume e margem.")
                elif status_vol == "Baixo":
                    st.info("🟡 **AGUARDAR VOLUME:** Preço acima da média, mas falta força compradora.")
                else:
                    st.info("🟡 **NEUTRO:** Preço muito próximo da SMA 50 ou tendência lateral.")
            else:
                st.error("🔴 **TENDÊNCIA DE BAIXA:** Ativo operando abaixo da média de 50 dias.")

            st.divider()
            
            # Ciclos de Resistência
            st.subheader("📊 Ciclos de Resistência e Risco")
            df_rec = df.iloc[-90:]
            max_90 = float(df_rec['High'].max())
            df_ant = df.iloc[:-90] if len(df) > 90 else None
            max_180 = float(df_ant['High'].max()) if df_ant is not None else max_90
            
            up90 = ((max_90 - preco_atual) / preco_atual) * 100
            up180 = ((max_180 - preco_atual) / preco_atual) * 100
            
            c1, c2 = st.columns(2)
            c1.info(f"Pico 0-90 dias: R$ {max_90:.22f} (Upside: {up90:.1f}%)")
            c2.info(f"Pico 90-180 dias: R$ {max_180:.2f} (Upside: {up180:.1f}%)")
            
            st.error(f"⚠️ Stop Loss Sugerido: R$ {preco_atual * (1 - (stop_loss_input / 100)):.2f}")
            st.caption(f"Análise baseada em dados históricos da B3 (Yahoo Finance).")
        else:
            st.error("Ativo não encontrado. Verifique o ticker (ex: B3SA3).")
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
