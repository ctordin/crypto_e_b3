import ccxt
import pandas as pd
import yfinance as yf
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURAÇÕES
# ==========================================
CORRETORA = ccxt.okx()
TIMEFRAME = '1d'

PORTFOLIO = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD',
    'SOL/USDT': 'SOL-USD', 'AVAX/USDT': 'AVAX-USD',
    'LINK/USDT': 'LINK-USD', 'ADA/USDT': 'ADA-USD'
}

def checar_fundamentos(ticker_yf):
    try:
        info = yf.Ticker(ticker_yf).info
        mkt_cap = info.get('marketCap', 1)
        vol_24h = info.get('volume24Hr', 0)
        giro_diario = (vol_24h / mkt_cap) * 100
        return giro_diario > 2.0
    except:
        return True # Libera se a API falhar

def obter_dados(simbolo):
    velas = CORRETORA.fetch_ohlcv(simbolo, TIMEFRAME, limit=100)
    df = pd.DataFrame(velas, columns=['timestamp', 'abertura', 'maxima', 'minima', 'fechamento', 'volume'])
    
    df['ema_rapida'] = df['fechamento'].ewm(span=9, adjust=False).mean()
    df['sma_50'] = df['fechamento'].rolling(window=50).mean()
    
    delta = df['fechamento'].diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = ganho / perda
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df.dropna()

print(f"📡 INICIANDO RADAR CRYPTO (PULLBACK DIÁRIO) - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
print("-" * 65)

for simbolo_okx, simbolo_yf in PORTFOLIO.items():
    if not checar_fundamentos(simbolo_yf):
        print(f"[{simbolo_okx}] ❌ REPROVADA (Baixa Liquidez/Giro)")
        continue
        
    df = obter_dados(simbolo_okx)
    atual = df.iloc[-1]
    anterior = df.iloc[-2]
    
    tendencia_alta = atual['fechamento'] > atual['sma_50']
    em_promocao = atual['rsi'] < 55
    rompeu_ema9 = atual['fechamento'] > atual['ema_rapida'] and anterior['fechamento'] <= anterior['ema_rapida']
    
    preco = atual['fechamento']
    
    if tendencia_alta and em_promocao and rompeu_ema9:
        print(f"[{simbolo_okx}] 🚀 GATILHO DE COMPRA! (Preço: ${preco:.2f} | RSI: {atual['rsi']:.1f})")
    elif tendencia_alta and em_promocao and not rompeu_ema9:
        print(f"[{simbolo_okx}] 👀 EM OBSERVAÇÃO (Barata, aguardando romper EMA 9. RSI: {atual['rsi']:.1f})")
    elif tendencia_alta and not em_promocao:
        print(f"[{simbolo_okx}] ⏳ ESTICADA (Aguarde uma correção. RSI: {atual['rsi']:.1f})")
    else:
        print(f"[{simbolo_okx}] ❌ TENDÊNCIA DE BAIXA (Abaixo da Média de 50 dias)")
        
    time.sleep(0.5)

print("-" * 65)
print("🎯 DICA: Use os parâmetros do Gabarito (Stop/Trailing) nas moedas com GATILHO ACIONADO.")