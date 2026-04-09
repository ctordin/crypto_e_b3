import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURAÇÕES
# ==========================================
LISTA_ACOES = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA',
    'WEGE3.SA', 'ABEV3.SA', 'RENT3.SA', 'SUZB3.SA', 'RADL3.SA',
    'ALOS3.SA'
]

def obter_dados_b3(ticker):
    try:
        df = yf.download(ticker, period='100d', interval='1d', progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        df = df.reset_index()
        df.rename(columns={'Close': 'fechamento'}, inplace=True)
        
        df['ema_rapida'] = df['fechamento'].ewm(span=9, adjust=False).mean()
        df['sma_50'] = df['fechamento'].rolling(window=50).mean()
        
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df.dropna()
    except:
        return None

print(f"🏢 INICIANDO RADAR B3 (PULLBACK DIÁRIO) - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
print("-" * 65)

for acao in LISTA_ACOES:
    df = obter_dados_b3(acao)
    
    if df is None or len(df) < 5:
        print(f"[{acao.replace('.SA', '')}] ⚠️ Erro ao baixar dados.")
        continue
        
    atual = df.iloc[-1]
    anterior = df.iloc[-2]
    
    tendencia_alta = float(atual['fechamento']) > float(atual['sma_50'])
    em_promocao = float(atual['rsi']) < 55
    rompeu_ema9 = float(atual['fechamento']) > float(atual['ema_rapida']) and float(anterior['fechamento']) <= float(anterior['ema_rapida'])
    
    preco = float(atual['fechamento'])
    nome = acao.replace('.SA', '')
    
    # Alinhamento estético no terminal
    tabs = "\t" if len(nome) < 5 else ""
    
    if tendencia_alta and em_promocao and rompeu_ema9:
        print(f"[{nome}]{tabs} 🚀 GATILHO DE COMPRA! (Preço: R${preco:.2f} | RSI: {atual['rsi']:.1f})")
    elif tendencia_alta and em_promocao and not rompeu_ema9:
        print(f"[{nome}]{tabs} 👀 EM OBSERVAÇÃO (Caiu, aguardando retomada. RSI: {atual['rsi']:.1f})")
    elif tendencia_alta and not em_promocao:
        print(f"[{nome}]{tabs} ⏳ ESTICADA (Aguarde corrigir. RSI: {atual['rsi']:.1f})")
    else:
        print(f"[{nome}]{tabs} ❌ TENDÊNCIA DE BAIXA (Abaixo da Média de 50)")

print("-" * 65)
print("🎯 DICA: Verifique se a ação teve bom desempenho no Otimizador antes de comprar.")