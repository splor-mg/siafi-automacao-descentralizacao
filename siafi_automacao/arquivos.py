"""Movimentação de arquivos entre as pastas do robô.

Compartilhado pelo consolida.py e pelo descentralizacao.py. Nada aqui lê o
.env: os caminhos chegam por parâmetro, para as funções serem testáveis sem
tocar nas pastas de verdade.

Estrutura dentro da pasta-raiz "Projeto de Descentralização" (PASTA_WINDOWS):

    Remanejados (Insira seu arquivo aqui)/   planilhas de entrada
    Conferencia/                             conferência em uso / última feita
    Realizados/Remanejamento Realizados/     entradas já consolidadas
    Realizados/Conferencia Realizados/       conferências anteriores

E na pasta local do Linux (PASTA_LINUX, por padrão <repo>/data):

    em_processamento/    conferência enquanto o robô está no SIAFI
    .movidos             manifesto da última consolidação (ver abaixo)
    .retomaveis          conferências que o robô devolveu interrompidas
"""

import fcntl
import os
import shutil
import time
from collections import namedtuple

import pandas as pd

SUB_REMANEJADOS = 'Remanejados (Insira seu arquivo aqui)'
SUB_CONFERENCIA = 'Conferencia'
SUB_REALIZADOS_REMANEJAMENTO = os.path.join('Realizados', 'Remanejamento Realizados')
SUB_REALIZADOS_CONFERENCIA = os.path.join('Realizados', 'Conferencia Realizados')

SUB_EM_PROCESSAMENTO = 'em_processamento'
NOME_MANIFESTO = '.movidos'
NOME_RETOMAVEIS = '.retomaveis'

# Aba das planilhas de entrada e da conferência
ABA = 'Execucao'



def numero_do_ambiente(nome, padrao):
    """Lê um número de uma variável de ambiente (do .env), ou o padrão.

    Lido na hora do uso, e não na importação do módulo: o .env só é carregado
    quando o programa começa, depois de este arquivo já ter sido importado.
    Valor ausente ou que não é número cai no padrão em vez de derrubar o robô.
    """
    try:
        return type(padrao)(os.getenv(nome) or padrao)
    except ValueError:
        return padrao


def mover_tentativas():
    """Retry para operações dentro de pastas sincronizadas pelo OneDrive: um
    arquivo recém-gravado pode ficar alguns segundos com um handle aberto pelo
    processo de sincronização do Windows, e mover/remover falha com
    PermissionError mesmo sem nada de errado."""
    return numero_do_ambiente('MOVER_TENTATIVAS', 6)


def mover_espera_segundos():
    return numero_do_ambiente('MOVER_ESPERA_SEGUNDOS', 2.0)


def retomada_max_dias():
    """Uma conferência com linhas por fazer só é retomada sozinha se tiver
    sido mexida há poucos dias. Sem este limite, um arquivo esquecido na pasta
    "Conferencia" (de uma falha antiga, que a pessoa já resolveu à mão no
    SIAFI) seria executado na primeira vez em que o robô rodasse com a pasta
    de entrada vazia."""
    return numero_do_ambiente('RETOMADA_MAX_DIAS', 7)


class ExecucaoEmAndamento(Exception):
    """Já existe outra execução do robô segurando a trava."""


# ---------------------------------------------------------------------------
# Trava de execução
# ---------------------------------------------------------------------------

def travar_execucao():
    """Impede duas execuções simultâneas. Devolve o arquivo da trava aberto.

    Dois cliques seguidos no atalho abriam dois robôs: os dois entram no SIAFI
    com o mesmo usuário (o mainframe recusa a segunda sessão) e mexem nas
    mesmas planilhas. A trava vale enquanto o arquivo devolvido estiver
    aberto: quem chama o fecha ao terminar (ver liberar_execucao).

    O caminho é o mesmo dos robôs de cota e de crédito (~/.siafi-robo.lock),
    de propósito: numa máquina com mais de um robô, todos usam o mesmo usuário
    do SIAFI.

    Levanta ExecucaoEmAndamento se a trava já estiver tomada. Se não for
    possível nem criar o arquivo, segue sem trava: ela é uma proteção a mais,
    não pode ser o motivo de o robô não rodar.
    """
    caminho = os.path.expanduser(os.getenv('SIAFI_LOCK') or '~/.siafi-robo.lock')
    try:
        trava = open(caminho, 'w')
    except OSError as e:
        print(f'[aviso] não consegui criar a trava de execução ({e}); seguindo sem ela.')
        return None
    try:
        fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        trava.close()
        raise ExecucaoEmAndamento()
    except OSError as e:
        trava.close()
        print(f'[aviso] não consegui tomar a trava de execução ({e}); seguindo sem ela.')
        return None
    return trava


def liberar_execucao(trava):
    """Solta a trava tomada por travar_execucao()."""
    if trava is not None:
        trava.close()


# ---------------------------------------------------------------------------
# Listagem e movimentação
# ---------------------------------------------------------------------------

def listar_xlsx(pasta):
    """Os .xlsx de uma pasta (caminhos completos), ignorando os arquivos de
    trava que o Excel cria ao lado de uma planilha aberta ('~$nome.xlsx')."""
    if not os.path.isdir(pasta):
        return []
    arquivos = []
    for nome in sorted(os.listdir(pasta)):
        if nome.startswith('~$') or not nome.lower().endswith('.xlsx'):
            continue
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho):
            arquivos.append(caminho)
    return arquivos


def _com_retry(operacao, descricao, tentativas, espera):
    """Executa 'operacao', tentando de novo se o arquivo estiver travado."""
    tentativas = mover_tentativas() if tentativas is None else tentativas
    espera = mover_espera_segundos() if espera is None else espera
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return operacao()
        except FileNotFoundError:
            raise                      # esperar não faz o arquivo aparecer
        except OSError as e:
            ultimo_erro = e
            if tentativa < tentativas:
                print(f'[aviso] arquivo travado (OneDrive sincronizando ou '
                      f'planilha aberta no Excel?). Tentativa '
                      f'{tentativa}/{tentativas} de {descricao}. '
                      f'Aguardando {espera}s...')
                time.sleep(espera)
    raise ultimo_erro


def mover(origem, destino, tentativas=None, espera=None):
    """Move 'origem' para o caminho 'destino', sobrescrevendo se já existir.

    copy_function=shutil.copyfile: entre o Linux e o /mnt/c o shutil.move
    copia e apaga; a cópia padrão (copy2) tenta levar junto permissões e
    datas, o que o drvfs do WSL nem sempre aceita.
    """
    def operacao():
        if os.path.exists(destino):
            os.remove(destino)
        shutil.move(origem, destino, copy_function=shutil.copyfile)

    _com_retry(operacao, f"mover '{os.path.basename(origem)}'", tentativas, espera)


def destino_livre(pasta, nome):
    """Caminho dentro de 'pasta' que ainda não existe: 'nome', depois
    'nome (1)', 'nome (2)'... Nada é sobrescrito."""
    destino = os.path.join(pasta, nome)
    base, ext = os.path.splitext(nome)
    i = 1
    while os.path.exists(destino):
        destino = os.path.join(pasta, f'{base} ({i}){ext}')
        i += 1
    return destino


def mover_para_pasta(origem, pasta_destino, tentativas=None, espera=None):
    """Move 'origem' para dentro de 'pasta_destino' sem sobrescrever nada.
    Devolve o caminho final."""
    os.makedirs(pasta_destino, exist_ok=True)
    destino = destino_livre(pasta_destino, os.path.basename(origem))
    _com_retry(
        lambda: shutil.move(origem, destino, copy_function=shutil.copyfile),
        f"mover '{os.path.basename(origem)}'", tentativas, espera)
    return destino


def remover(caminho, tentativas=None, espera=None):
    """Remove um arquivo, com o mesmo retry. Arquivo ausente não é erro."""
    def operacao():
        try:
            os.remove(caminho)
        except FileNotFoundError:
            pass

    _com_retry(operacao, f"remover '{os.path.basename(caminho)}'", tentativas, espera)


# ---------------------------------------------------------------------------
# Conferências: o que ainda falta fazer
# ---------------------------------------------------------------------------

Conferencia = namedtuple('Conferencia', 'caminho pendentes preenchidas modificada')


def contar_linhas(caminho):
    """(pendentes, preenchidas) de uma conferência.

    Pendente é a linha com dados e a coluna 'Progresso' vazia — o mesmo
    critério que o descentralizacao.py usa para montar a fila. Arquivo que não
    dá para ler conta como (0, 0): não é ele que o robô vai processar.
    """
    try:
        df = pd.read_excel(caminho, sheet_name=ABA)
    except Exception as e:
        print(f"[aviso] não consegui ler '{os.path.basename(caminho)}' ({e}).")
        return 0, 0

    df = df.dropna(how='all')
    if 'Progresso' not in df.columns:
        return len(df), 0

    progresso = df['Progresso']
    sem_progresso = progresso.isna() | (progresso.astype(str).str.strip() == '')
    pendentes = int(sem_progresso.sum())
    return pendentes, len(df) - pendentes


def listar_conferencias(pasta):
    """As conferências de uma pasta com a contagem de linhas, da mais antiga
    para a mais recente."""
    conferencias = []
    for caminho in listar_xlsx(pasta):
        pendentes, preenchidas = contar_linhas(caminho)
        conferencias.append(Conferencia(caminho, pendentes, preenchidas,
                                        os.path.getmtime(caminho)))
    conferencias.sort(key=lambda c: c.modificada)
    return conferencias


def dias_parada(conferencia, agora=None):
    """Há quantos dias (inteiros) a conferência foi mexida pela última vez."""
    agora = time.time() if agora is None else agora
    return int(max(0, agora - conferencia.modificada) // 86400)


def escolher_para_processar(conferencias, agora=None, permitidas=None):
    """Entre as conferências listadas, a que o robô deve processar agora, ou
    None.

    É a mais recente que tem linha pendente, foi mexida há no máximo
    retomada_max_dias() e está em 'permitidas' (caminhos absolutos; None = sem
    esse filtro) — seja a que o consolida.py acabou de gerar, seja a de uma
    execução interrompida que está sendo retomada (ver retomaveis()).
    """
    limite = retomada_max_dias()
    candidatas = [c for c in conferencias
                  if c.pendentes > 0 and dias_parada(c, agora) <= limite
                  and (permitidas is None or os.path.abspath(c.caminho) in permitidas)]
    return max(candidatas, key=lambda c: c.modificada) if candidatas else None


def conferencia_a_processar(pasta, agora=None, permitidas=None):
    """O mesmo que escolher_para_processar(), lendo a pasta."""
    return escolher_para_processar(listar_conferencias(pasta), agora, permitidas)


# ---------------------------------------------------------------------------
# Conferências que podem ser retomadas sem planilha nova
#
# Só a que ESTE robô devolveu interrompida. Uma conferência que tenha ficado
# na pasta "Conferencia" de outro jeito (deixada pela versão anterior, que não
# marcava a linha em curso, ou mexida à mão) pode ter linhas em branco que já
# estão no SIAFI — inclusive lançadas à mão pelo órgão depois de uma falha — e
# executá-la sozinha duplicaria a operação.
# ---------------------------------------------------------------------------

def retomaveis(registro):
    """Os caminhos (absolutos) das conferências que o robô devolveu
    interrompidas."""
    try:
        with open(registro, encoding='utf-8') as f:
            return {linha.strip() for linha in f if linha.strip()}
    except OSError:
        return set()


def marcar_retomavel(registro, caminho):
    caminho = os.path.abspath(caminho)
    if caminho in retomaveis(registro):
        return
    try:
        os.makedirs(os.path.dirname(registro), exist_ok=True)
        with open(registro, 'a', encoding='utf-8') as f:
            f.write(caminho + '\n')
    except OSError as e:
        print(f"[aviso] não consegui registrar '{os.path.basename(caminho)}' "
              f"para ser retomada ({e}): ela não será continuada sozinha.")


def desmarcar_retomavel(registro, caminho):
    """A conferência foi até o fim: não há mais o que retomar nela."""
    caminho = os.path.abspath(caminho)
    atuais = retomaveis(registro)
    if caminho not in atuais:
        return
    try:
        with open(registro, 'w', encoding='utf-8') as f:
            f.writelines(c + '\n' for c in sorted(atuais - {caminho}))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Manifesto da consolidação
#
# O consolida.py tira as planilhas de entrada da fila ANTES de o robô entrar
# no SIAFI. Se o robô parar antes de enviar qualquer coisa (VPN fora, senha
# expirada, login recusado), elas precisam voltar: sem isso a pessoa resolve o
# problema, roda de novo e recebe "nenhuma planilha para processar".
#
# O manifesto guarda o que a última consolidação fez, uma linha por item:
#     C<TAB>caminho da conferência criada
#     M<TAB>para onde o arquivo foi<TAB>de onde ele saiu
# Gravado item a item: se a consolidação cair no meio, o que já foi movido
# está registrado.
# ---------------------------------------------------------------------------

def iniciar_manifesto(manifesto):
    """Começa um manifesto vazio. O de uma execução anterior não vale para
    esta: se ficasse, um 'desfazer' poderia mexer em planilhas já enviadas."""
    os.makedirs(os.path.dirname(manifesto), exist_ok=True)
    with open(manifesto, 'w', encoding='utf-8'):
        pass


def _anotar(manifesto, *campos):
    with open(manifesto, 'a', encoding='utf-8') as f:
        f.write('\t'.join(campos) + '\n')


def registrar_conferencia(manifesto, caminho):
    _anotar(manifesto, 'C', caminho)


def registrar_movido(manifesto, destino, origem):
    _anotar(manifesto, 'M', destino, origem)


def ler_manifesto(manifesto):
    """Devolve (conferencia, movidos): o caminho da conferência criada (ou
    None) e a lista de (destino, origem). Sem manifesto: (None, [])."""
    conferencia = None
    movidos = []
    try:
        with open(manifesto, encoding='utf-8') as f:
            for linha in f:
                campos = linha.rstrip('\n').split('\t')
                if campos[0] == 'C' and len(campos) == 2:
                    conferencia = campos[1]
                elif campos[0] == 'M' and len(campos) == 3:
                    movidos.append((campos[1], campos[2]))
    except OSError:
        pass
    return conferencia, movidos


def descartar_manifesto(manifesto):
    """Apaga o manifesto: daqui em diante a consolidação não se desfaz mais."""
    try:
        os.remove(manifesto)
    except OSError:
        pass


def desfazer_consolidacao(manifesto, conferencia_atual=None):
    """Desfaz a última consolidação: apaga a conferência gerada e devolve cada
    arquivo para o lugar de onde saiu. Só pode ser chamada enquanto NADA foi
    enviado ao SIAFI.

    'conferencia_atual' é onde a conferência está agora, se já saiu do lugar
    em que foi criada (o robô a traz para a pasta local).

    Nunca levanta exceção: roda durante o tratamento de outra falha, e mascarar
    o erro original só atrapalharia. Devolve (devolvidos, nao_devolvidos):
    os caminhos para onde os arquivos voltaram e os nomes dos que não deu
    para devolver.
    """
    conferencia, movidos = ler_manifesto(manifesto)
    devolvidos = []
    nao_devolvidos = []

    # A conferência sai primeiro: uma anterior, do mesmo dia, pode voltar para
    # a pasta com exatamente o mesmo nome.
    for caminho in {conferencia_atual, conferencia} - {None}:
        try:
            remover(caminho)
        except OSError as e:
            print(f"[aviso] não consegui apagar '{caminho}': {e}")

    # De trás para frente: o que foi movido por último volta primeiro.
    for destino, origem in reversed(movidos):
        nome = os.path.basename(origem)
        try:
            if not os.path.exists(destino):
                continue               # alguém já mexeu nele à mão
            if os.path.exists(origem):
                # Já há outro arquivo com esse nome na fila (a versão
                # corrigida, provavelmente). Sobrescrever apagaria o trabalho
                # da pessoa sem aviso.
                print(f"[aviso] já existe '{origem}'; mantive '{destino}' onde está.")
                nao_devolvidos.append(nome)
                continue
            os.makedirs(os.path.dirname(origem), exist_ok=True)
            mover(destino, origem)
            devolvidos.append(origem)
        except OSError as e:
            print(f"[aviso] não consegui devolver '{destino}': {e}")
            nao_devolvidos.append(nome)

    descartar_manifesto(manifesto)
    return devolvidos, nao_devolvidos


# ---------------------------------------------------------------------------
# Conferência que ficou para trás na pasta local
# ---------------------------------------------------------------------------

def recuperar_interrompidas(pasta_em_processamento, pasta_conferencia, registro=None):
    """Devolve para "Conferencia" o que uma execução anterior deixou na pasta
    local, registrando-a para ser retomada. Devolve a lista de caminhos
    devolvidos.

    Acontece quando a janela do robô é fechada no meio (ou o computador
    desliga): o processo morre sem chance de devolver a planilha, e ela ficava
    para sempre dentro do WSL, onde ninguém a procura. A linha que estava em
    curso já está marcada no arquivo (ver PROGRESSO_INCERTO), então devolver é
    seguro.

    Só olha a subpasta 'em_processamento', que é criada por esta versão do
    robô. Arquivo solto na pasta local, de versões antigas, fica onde está:
    não dá para saber de quando é nem o que já foi feito à mão no SIAFI.
    """
    devolvidas = []
    for caminho in listar_xlsx(pasta_em_processamento):
        try:
            destino = mover_para_pasta(caminho, pasta_conferencia)
        except OSError as e:
            print(f"[aviso] a conferência '{os.path.basename(caminho)}' de uma "
                  f"execução interrompida continua em '{caminho}': {e}")
            continue
        print(f"Conferência de uma execução interrompida devolvida para: {destino}")
        if registro:
            marcar_retomavel(registro, destino)
        devolvidas.append(destino)
    return devolvidas
