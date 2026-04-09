import ccxt
import pandas as pd
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÕES (O GABARITO DO OTIMIZADOR)
# ==========================================
CORRETORA = ccxt.okx()
SÍMBOLO = 'SOL/USDT'
TIMEFRAME = '1d'

# Insira aqui os dados que o Otimizador encontrou para esta moeda/ação
STOP_LOSS_PCT = 0.04      # 4% de Stop Loss
TRAILING_STOP_PCT = 0.20  # 20% de Trailing Stop
RSI_MAX_ENTRADA = 52      # Nível máximo de RSI para considerar "Promoção"

def limpar_ecra():
    os.system('cls' if os.name == 'nt' else 'clear')

# ==========================================
# 2. COLETA E CÁLCULO DE DADOS
# ==========================================
def obter_dados():
    velas = CORRETORA.fetch_ohlcv(SÍMBOLO, TIMEFRAME, limit=100)
    df = pd.DataFrame(velas, columns=['timestamp', 'abertura', 'maxima', 'minima', 'fechamento', 'volume'])
    
    # Indicadores
    df['ema_rapida'] = df['fechamento'].ewm(span=9, adjust=False).mean()
    df['ema_lenta'] = df['fechamento'].ewm(span=21, adjust=False).mean()
    df['sma_50'] = df['fechamento'].rolling(window=50).mean()
    
    delta = df['fechamento'].diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = ganho / perda
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df.dropna()

def analisar_ativo():
    try:
        df = obter_dados()
        atual = df.iloc[-1]
        anterior = df.iloc[-2]

        preco = atual['fechamento']

        # Verificações da Estratégia de Pullback
        tendencia_alta = preco > atual['sma_50']
        moeda_corrigiu = atual['rsi'] < RSI_MAX_ENTRADA
        rompeu_ema9 = preco > atual['ema_rapida'] and anterior['fechamento'] <= anterior['ema_rapida']

        # Cálculo das Zonas de Risco da Operação
        valor_stop_loss = preco * (1 - STOP_LOSS_PCT)
        valor_alvo_trailing = preco * (1 + TRAILING_STOP_PCT) # Onde o trailing de 20% começa a fazer um grande efeito

        # Lógica de Recomendação
        if tendencia_alta and moeda_corrigiu and rompeu_ema9:
            recomendacao = "🟢 COMPRA IMEDIATA (Gatilho Acionado!)"
            status = "O ativo está em tendência de alta, corrigiu o suficiente e retomou a força hoje."
        elif tendencia_alta and moeda_corrigiu and not rompeu_ema9:
            recomendacao = "👀 PREPARAR COMPRA (Aguardar Gatilho)"
            status = "O ativo está com um excelente desconto, mas ainda está a cair. Aguarde o preço fechar acima da EMA 9."
        elif tendencia_alta and not moeda_corrigiu:
            recomendacao = "⏳ MANTER / NÃO COMPRAR MAIS (Esticado)"
            status = "O ativo já subiu bastante. Se já tem a moeda, deixe o Trailing Stop rolar. Se não tem, não compre agora."
        else:
            recomendacao = "🔴 FORA DO MERCADO (Tendência de Baixa)"
            status = "A maré está contra. O preço está abaixo da Média Macro de 50 dias. Risco elevado."

        return atual, recomendacao, status, valor_stop_loss, valor_alvo_trailing

    except Exception as e:
        return None, f"Erro: {e}", "", 0, 0

# ==========================================
# 3. PAINEL DO CONSELHEIRO QUANTITATIVO
# ==========================================
def relatorio_detalhado():
    limpar_ecra()
    print(f" A ligar aos servidores da OKX para análise de {SÍMBOLO}...\n")
    
    atual, recomendacao, status, stop, alvo_trailing = analisar_ativo()
    
    if atual is None:
        print(recomendacao)
        return

    preco = atual['fechamento']

    print("======================================================")
    print(f" 🤖 CONSELHEIRO QUANTITATIVO: {SÍMBOLO}")
    print(f" 📅 Data da Análise: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("======================================================")
    print(" 📊 RADIOGRAFIA DO ATIVO:")
    print(f"    Preço Atual:    ${preco:.2f}")
    print(f"    Média Macro (50): ${atual['sma_50']:.2f} -> {'✅ Alta' if preco > atual['sma_50'] else '❌ Baixa'}")
    print(f"    Gatilho EMA (9):  ${atual['ema_rapida']:.2f} -> {'✅ Rompida' if preco > atual['ema_rapida'] else '❌ Abaixo'}")
    print(f"    RSI (Desconto):   {atual['rsi']:.1f} / {RSI_MAX_ENTRADA} Max -> {'✅ Na Promoção' if atual['rsi'] < RSI_MAX_ENTRADA else '❌ Caro'}")
    print("------------------------------------------------------")
    print(f" 🎯 VEREDICTO DE HOJE:")
    print(f"    >> {recomendacao}")
    print(f"    >> {status}")
    print("------------------------------------------------------")
    
    # Exibe as métricas de gestão de risco apenas se a recomendação for de compra
    if "COMPRA IMEDIATA" in recomendacao:
        print(" 🛡️ GESTÃO DE RISCO ESTRITA (Baseada no Gabarito):")
        print(f"    1. Onde colocar o STOP LOSS ({STOP_LOSS_PCT*100:.0f}%): ${stop:.2f}")
        print(f"    2. Alvo Base para Trailing ({TRAILING_STOP_PCT*100:.0f}%): ${alvo_trailing:.2f}")
        print("       (Nota: Se a moeda bater no Alvo Base e cair, o lucro é garantido!)")
    
    print("======================================================")

if __name__ == '__main__':
    relatorio_detalhado()