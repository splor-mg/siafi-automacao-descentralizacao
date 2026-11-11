"""Aviso de atualização na janela do robô.

Na primeira execução depois de o robô se atualizar (git pull), mostra na
janela o texto do NOVIDADES.txt, uma vez só em cada computador. Para avisar os
órgãos de uma mudança, basta trocar o texto desse arquivo: texto diferente
aparece de novo, uma vez, em cada computador.

É chamado pelo consolida.py, e não pelo robo.ps1, de propósito: o robo.ps1 em
execução é o de antes do git pull (o PowerShell já o leu inteiro), e uma
mudança nele só valeria a partir da segunda execução. O consolida.py é lido do
disco depois do pull, por qualquer versão do lançador.

Nada aqui pode impedir o robô de rodar: qualquer falha só deixa de mostrar o
aviso.
"""

import hashlib
import os
import sys
import time

LARGURA = 78

# Tempo para ler antes de o resto da execução empurrar o aviso para fora da tela
PAUSA_SEGUNDOS = 10

# Fica na pasta local (data/), fora do Git: cada computador tem o seu.
NOME_MARCADOR = '.novidades_vistas'


def ler_texto(caminho):
    """O texto do aviso, sem as linhas de comentário (começadas por '#') e sem
    linhas em branco nas pontas. Vazio se o arquivo não existir."""
    try:
        with open(caminho, encoding='utf-8-sig') as f:
            linhas = [l.rstrip() for l in f if not l.lstrip().startswith('#')]
    except OSError:
        return ''
    return '\n'.join(linhas).strip('\n')


def assinatura(texto):
    """Identifica o texto: muda quando o texto muda."""
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()[:16]


def _em_terminal():
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def mostrar(arquivo, marcador, pausa=PAUSA_SEGUNDOS, terminal=None):
    """Mostra o aviso se o texto mudou desde a última vez neste computador.
    Devolve True se mostrou.

    A pausa só acontece numa janela de verdade: o robo.ps1 embutido no .exe
    antigo relança o robô engolindo toda a saída, e lá ninguém vê o aviso."""
    texto = ler_texto(arquivo)
    if not texto.strip():
        return False

    sig = assinatura(texto)
    try:
        with open(marcador, encoding='utf-8') as f:
            if f.read().strip() == sig:
                return False
    except OSError:
        pass

    print()
    print('=' * LARGURA)
    for linha in texto.splitlines():
        print(f'  {linha}'.rstrip())
    print('=' * LARGURA)
    print(flush=True)

    try:
        os.makedirs(os.path.dirname(marcador), exist_ok=True)
        with open(marcador, 'w', encoding='utf-8') as f:
            f.write(sig + '\n')
    except OSError as e:
        print(f'[aviso] não consegui registrar que o aviso foi visto ({e}); '
              f'ele vai aparecer de novo na próxima execução.')

    if pausa and (_em_terminal() if terminal is None else terminal):
        time.sleep(pausa)
    return True
