"""Utilidades do emulador 3270: conexão, teclado e leitura da tela.

Trazidas dos robôs de cota e de crédito, onde cada uma nasceu de uma execução
que quebrou em produção.
"""

import time

from py3270 import CommandError, Emulator

LINHAS = 24
COLUNAS = 80

MSG_SESSAO_RECUSADA = 'UNABLE TO ESTABLISH SESSION'
MSG_INCONSISTENCIA = 'Inconsistencia no Registro da Contabilizacao'

# ....:....1....:....2 ... para localizar a coluna de um campo de relance
_REGUA = ''.join(
    str(c // 10) if c % 10 == 0 else (':' if c % 5 == 0 else '.')
    for c in range(1, COLUNAS + 1)
)


class FalhaDeConexao(Exception):
    """Não foi possível abrir a sessão no SIAFI."""


def encerrar_emulador(em, avisar=True):
    """Encerra o emulador ignorando falhas.

    Usado no caminho feliz e no tratamento de erro: se a sessão já caiu o
    terminate() pode estourar, e isso não pode impedir o que vem depois dele
    (devolver a planilha para a pasta de conferência)."""
    if em is None:
        return
    try:
        em.terminate()
    except Exception as e:
        if avisar:
            print(f'[aviso] falha ao encerrar o emulador (ignorando): {e}')
        # O terminate() estourou antes de fechar o processo do x3270/s3270.
        # Fecha direto e marca como encerrado: sem isso o processo ficava
        # pendurado e o py3270 tentava de novo ao descartar o objeto, jogando
        # um traceback solto na janela de quem está usando.
        try:
            em.app.close()
        except Exception:
            pass
        em.is_terminated = True


def conectar_siafi(host, visivel, tentativas=3, espera=3, criar_emulador=Emulator):
    """Abre o emulador e conecta ao SIAFI, tentando de novo até 'tentativas'
    vezes. Devolve o emulador conectado ou levanta FalhaDeConexao.

    Além da recusa de sessão do próprio mainframe, trata a falha do
    Emulator()/connect() em si (VPN desligada, host inacessível, x3270
    ausente), que antes subia como traceback cru."""
    ultimo_motivo = None
    for tentativa in range(1, tentativas + 1):
        em = None
        try:
            em = criar_emulador(visible=visivel)
            em.connect(host)
            em.wait_for_field()
            if not em.string_found(1, 2, MSG_SESSAO_RECUSADA):
                return em
            ultimo_motivo = f'o servidor recusou a sessão ({MSG_SESSAO_RECUSADA})'
        except Exception as e:
            ultimo_motivo = f'{type(e).__name__}: {e}'

        encerrar_emulador(em, avisar=False)
        print(f'Tentativa {tentativa}/{tentativas} de conectar em {host} '
              f'falhou: {ultimo_motivo}')
        if tentativa < tentativas:
            print(f'Aguardando {espera}s antes de tentar de novo...')
            time.sleep(espera)

    raise FalhaDeConexao(ultimo_motivo)


def esperar_teclado(em, segundos=10):
    """Espera o mainframe destravar o teclado antes de digitar.

    O py3270 sobe o emulador com unlockDelay desligado, e o SIAFI é um dos
    hosts que liberam o teclado antes de terem processado o comando: no robô
    de cota uma execução morreu no meio de uma linha com 'Keyboard locked'
    depois de o wait_for_field() já ter passado.

    Se o teclado não destravar no prazo, segue mesmo assim: o fill_field
    seguinte falha com a mensagem clara do py3270 e a linha fica marcada para
    conferência humana.
    """
    try:
        em.exec_command(f'Wait({segundos}, Unlock)'.encode('ascii'))
    except CommandError:
        pass


def ler_tela(em):
    """As 24 linhas da tela. Lista vazia se o emulador não responder.

    Ler a tela não depende do teclado: funciona mesmo depois de um
    'Keyboard locked'."""
    try:
        return [em.string_get(l, 1, COLUNAS).rstrip()
                for l in range(1, LINHAS + 1)]
    except Exception:
        return []


def tela_contem(em, texto):
    """O texto aparece em alguma linha da tela? (sem diferenciar maiúsculas)

    Varre a tela inteira em vez de apostar numa linha fixa: errar a linha faz
    o robô seguir adiante e morrer mais à frente, escondendo o motivo real.
    """
    return texto.upper() in '\n'.join(ler_tela(em)).upper()


def senha_expirada(em):
    """O SIAFI está avisando que a senha expirou?"""
    return tela_contem(em, 'SENHA EXPIRADA')


def imprimir_tela(em, motivo):
    """'Print' da tela do SIAFI em texto, com a régua de colunas e o número de
    cada linha — as mesmas coordenadas do fill_field() e do string_get().

    Serve para entender por que o SIAFI não foi para a tela que o robô
    esperava: sem isto a janela só mostra 'Keyboard locked', que é o sintoma,
    nunca a mensagem do SIAFI que explica a causa.

    Nunca levanta exceção: roda durante o tratamento de outra falha. Devolve
    as linhas lidas.
    """
    if em is None:
        return []
    linhas = ler_tela(em)

    print()
    print(f'  ----- TELA DO SIAFI: {motivo} -----')
    if not linhas:
        print('  (não foi possível ler a tela: o emulador não respondeu)')
    else:
        print(f'      {_REGUA}')
        for numero, linha in enumerate(linhas, 1):
            print(f'  {numero:02d}| {linha}')
    print('  ' + '-' * (COLUNAS + 4))
    return linhas


def numero_apos(linha, marcador):
    """O primeiro 'pedaço' de texto depois de 'marcador' na linha, ou ''.

    Quando o SIAFI recusa o documento o rótulo continua na tela, mas sem
    número depois dele. Por isso não se assume que há algo para ler: o split()
    de um texto vazio devolve lista vazia, e o [0] disso derrubava o robô
    DEPOIS de a confirmação já ter sido enviada.
    """
    posicao = linha.find(marcador)
    if posicao == -1:
        return ''
    depois = linha[posicao + len(marcador):].split()
    return depois[0] if depois else ''
