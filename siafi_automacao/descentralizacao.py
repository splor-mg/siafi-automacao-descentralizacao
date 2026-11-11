"""Robô de descentralização de cota orçamentária no SIAFI.

Roda depois do consolida.py. Em ordem:

1. Devolve para "Conferencia" o que uma execução interrompida tenha deixado na
   pasta local, e escolhe a conferência com linhas pendentes.
2. Traz a conferência para a pasta local (Linux): gravar ali é rápido e não
   esbarra nas travas do OneDrive.
3. Confere a configuração e TODAS as linhas pendentes antes do login.
4. Entra no SIAFI e lança cada linha, gravando o resultado na coluna
   'Progresso' linha a linha.
5. Formata a planilha e a devolve para "Conferencia".

O que acontece quando algo dá errado (é o que quem usa precisa saber):

- Parou ANTES de enviar qualquer linha (VPN fora, senha expirada, login
  recusado, .env incompleto): nada foi feito no SIAFI. Se a conferência foi
  gerada nesta execução, a consolidação é desfeita — as planilhas voltam para
  a pasta de entrada. Se era uma retomada, a conferência volta intacta.
- Parou NO MEIO: a conferência volta para "Conferencia" com o que já foi
  feito. A linha que estava em curso fica marcada com PROGRESSO_INCERTO e não
  é refeita sozinha; as seguintes continuam em branco e são feitas na próxima
  execução.

Códigos de saída (lidos pelo robo.ps1):

    0  - foi até o fim (pode haver linha recusada pelo SIAFI: veja a planilha)
    1  - erro
    3  - senha do SIAFI expirada
    10 - já existe outra execução em andamento
    130 - interrompido pelo usuário (Ctrl+C)
"""

import os
import sys
import time

import pandas as pd
from dotenv import load_dotenv
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from py3270 import Emulator

import arquivos
from emulador import (FalhaDeConexao, conectar_siafi, encerrar_emulador,
                      imprimir_tela, senha_expirada)
from fluxo_anular_desc import anulacao
from fluxo_aprovar_desc import aprovacao
from fluxo_desc import MSG_INCONSISTENCIA, MSG_NAO_CONFIRMADA
from validacao import COLUNAS_OBRIGATORIAS, descrever_erros, validar_linha, vazio

# Raiz do repositório (siafi_automacao/descentralizacao.py -> sobe um nível)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SISTEMA = 'simg'
SIAFI_HOST_PADRAO = 'bhmvsb.prodemge.gov.br'

CODIGO_ERRO = 1
CODIGO_SENHA_EXPIRADA = 3
CODIGO_EM_ANDAMENTO = 10
CODIGO_INTERROMPIDO = 130

# Marca da linha cuja operação pode ter chegado ao SIAFI sem o robô ter lido o
# retorno. É gravada ANTES de a linha ser enviada e trocada pelo resultado
# depois: assim ela fica no arquivo mesmo que a janela do robô seja fechada no
# meio. Precisa ser texto não vazio — é isso que tira a linha da fila e obriga
# uma conferência humana antes de refazer.
PROGRESSO_INCERTO = 'INTERROMPIDA - VERIFICAR NO SIAFI'
PROGRESSO_SEM_RETORNO = 'SEM RETORNO DO SIAFI - VERIFICAR NO SIAFI'
PREFIXO_LINHA_INVALIDA = 'Linha inválida: '

# Tamanho máximo de cada campo na tela do SIAFI
LIMITES_CONFIG = [
    ('USUARIO', 'usuario', 8),
    ('SENHA', 'senha', 8),
    ('UNIDADE_EXECUTORA', 'unidade_executora', 7),
    ('UNIDADE_ORCAMENTARIA', 'unidade_orcamentaria', 4),
]


class Parada(Exception):
    """O robô parou por um motivo conhecido, que a mensagem explica a quem está
    usando. Não é bug: sai sem traceback, com o código de saída indicado."""

    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def carregar_config():
    """Lê o .env da raiz do repositório."""
    # utf-8-sig: o Bloco de Notas do Windows, usado para trocar a senha, pode
    # gravar um BOM no começo do arquivo e estragar o nome da primeira chave.
    load_dotenv(os.path.join(BASE_DIR, '.env'), encoding='utf-8-sig')
    return {
        'usuario': os.getenv('USUARIO'),
        'senha': os.getenv('SENHA'),
        'unidade_executora': os.getenv('UNIDADE_EXECUTORA'),
        'unidade_orcamentaria': os.getenv('UNIDADE_ORCAMENTARIA'),
        # Pasta-raiz "Projeto de Descentralização" (Windows/OneDrive, via /mnt/c)
        'pasta_windows': os.getenv('PASTA_WINDOWS'),
        # Pasta de trabalho local (Linux); se ausente, <repo>/data
        'pasta_local': os.getenv('PASTA_LINUX') or os.path.join(BASE_DIR, 'data'),
        'host': os.getenv('SIAFI_HOST') or SIAFI_HOST_PADRAO,
        # A janela do x3270 depende do WSLg. SIAFI_VISIVEL=false roda sem ela.
        'visivel': (os.getenv('SIAFI_VISIVEL') or 'true').strip().lower() != 'false',
        'conexao_tentativas': arquivos.numero_do_ambiente('CONEXAO_TENTATIVAS', 3),
    }


def validar_configuracao(cfg):
    """Problemas do .env que impediriam o login. Lista vazia se está tudo certo.

    Conferido antes de abrir o SIAFI: valor maior que o campo fazia o py3270
    estourar com o próprio valor na mensagem — inclusive a senha, na tela."""
    problemas = []
    for nome, chave, limite in LIMITES_CONFIG:
        valor = cfg.get(chave)
        if not valor:
            problemas.append(f'{nome} não está preenchido')
        elif len(valor) > limite:
            problemas.append(f'{nome} tem mais de {limite} caracteres, e o '
                             f'campo do SIAFI aceita no máximo {limite}')
    return problemas


# ---------------------------------------------------------------------------
# Planilha
# ---------------------------------------------------------------------------

def salvar_progresso(df, caminho, pasta_tmp):
    """Grava o DataFrame na conferência de forma atômica: escreve num arquivo
    temporário e troca. O temporário fica fora da pasta da conferência para
    não ser confundido com uma planilha."""
    tmp = os.path.join(pasta_tmp, '_tmp_progresso.xlsx')
    with pd.ExcelWriter(tmp, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=arquivos.ABA, index=False)
    os.replace(tmp, caminho)


def traduzir_progresso(retorno, nr_doc=''):
    """Converte a mensagem crua do SIAFI no texto que vai para a coluna
    'Progresso'. Sucesso ('REGISTRO EFETUADO') vira 'Ok - <nr do documento>';
    mensagens de erro conhecidas viram um texto amigável; qualquer outro retorno
    é mantido como veio, para nada ser escondido. Para incluir novas mensagens,
    basta acrescentar uma linha no mapa abaixo.

    Nunca devolve texto vazio: a linha já foi enviada, e 'Progresso' em branco
    faria a execução seguinte enviá-la de novo."""
    retorno = (retorno or '').strip()
    nr_doc = (nr_doc or '').strip()
    if retorno == '':
        return PROGRESSO_SEM_RETORNO

    # Sucesso: registra o Nr. do Documento Global junto do 'Ok'
    if 'REGISTRO EFETUADO' in retorno.upper():
        return f'Ok - {nr_doc}' if nr_doc else 'Ok'

    if retorno.startswith("E90 - SALDO ZERADO NA CONTA"):
        return 'Saldo zerado na conta'
    # O número entre parênteses no fim da Z03 pode variar.
    if retorno.startswith("Z03-SIAFI INDISPONIVEL PARA ATUALIZACAO DE DADOS"):
        return 'SIAFI indisponível para atualização, tente mais tarde'

    mapa = {
        "0139- PROJ/ATIV OU FONTE/PROC./IAG INEXISTENTE PARA UO":
            'Proj/Ativ ou Fonte/Proc./IAG inexistente para a UO',
        "0101- NATUREZA DESPESA INEXISTENTE(S).":
            'Natureza de despesa inexistente',
        "0101- GRUPO DESPESA INEXISTENTE(S).":
            'Grupo de despesa inexistente',
        "0139- PROGRAMA DE TRABALHO NAO ENCONTRADO PARA GM/FP.":
            'Programa de trabalho não encontrado para GM/FP',
        "0109-INFORME NATUREZA DE DESPESA COMPLETA.":
            'Informe a natureza de despesa completa',
        "0139- NAO EXITE DESCENTRALIZACAO PARA PROJ/ATIV OU FONTE/PROC./IAG":
            'Não existe descentralização para Proj/Ativ ou Fonte/Proc./IAG',
        "0139- SALDO INEXISTENTE A ANULAR PARA PROJ/ATIV":
            'Saldo inexistente a anular para Proj/Ativ',
        "0139- VALOR A APROVAR MAIOR QUE SALDO DISPONIVEL NO PROJ/ATIV.":
            'Valor a aprovar maior que o saldo disponível',
        "SALDO DE CREDITO ORCAMENTARIO A APROVAR POR PROJ/ATIV ZERADO.":
            'Saldo de crédito a aprovar zerado',
        "0139- VALOR A DESCENTRALIZAR MAIOR QUE SALDO APROVADO.":
            'Valor a descentralizar maior que o saldo aprovado',
        "0139- VALOR INFORMADO ALEM DO VALOR DESCENTRALIZADO PARA O PROJETO/ATIVIDADE":
            'Valor informado além do valor descentralizado',
        # 0017 ainda na tela depois dos dois PF5: a operação não foi gravada.
        MSG_NAO_CONFIRMADA:
            'Operação não confirmada no SIAFI',
        MSG_INCONSISTENCIA:
            'Erro de saldo contábil',
    }
    return mapa.get(retorno, retorno)


def formatar_planilha(ws):
    """Aplica formatação visual gerencial na aba: cabeçalho colorido, coluna
    'Valor' no formato xxx.xxx,xx, zebra nas linhas, coluna 'Progresso' com cor
    condicional (Ok = verde, erros = vermelho/amarelo, linha a conferir no
    SIAFI = laranja) e larguras ajustadas."""
    AZUL_ESCURO  = PatternFill('solid', fgColor='1F4E79')
    AZUL_CLARO   = PatternFill('solid', fgColor='D6E4F0')
    BRANCO       = PatternFill('solid', fgColor='FFFFFF')
    VERDE        = PatternFill('solid', fgColor='C6EFCE')
    AMARELO      = PatternFill('solid', fgColor='FFEB9C')
    VERMELHO     = PatternFill('solid', fgColor='FFC7CE')
    LARANJA      = PatternFill('solid', fgColor='F4B084')
    FONTE_BRANCA = Font(bold=True, color='FFFFFF', name='Calibri', size=11)
    FONTE_NORMAL = Font(name='Calibri', size=10)
    BORDA = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF'),
    )
    COLS_VALOR = {'Valor'}

    max_col = ws.max_column
    max_row = ws.max_row

    # Mapeia nome da coluna -> índice
    cabec = {ws.cell(row=1, column=c).value: c for c in range(1, max_col + 1)}

    # Remove linhas de grade
    ws.sheet_view.showGridLines = False

    # Cabeçalho
    for c in range(1, max_col + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill   = AZUL_ESCURO
        cell.font   = FONTE_BRANCA
        cell.border = BORDA
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=False)
    ws.row_dimensions[1].height = 20

    # Linhas de dados
    for r in range(2, max_row + 1):
        zebra = AZUL_CLARO if r % 2 == 0 else BRANCO
        for c in range(1, max_col + 1):
            cell      = ws.cell(row=r, column=c)
            cell.fill = zebra
            cell.font = FONTE_NORMAL
            cell.border = BORDA

            col_nome = ws.cell(row=1, column=c).value

            # Formata a coluna de valor monetário no padrão xxx.xxx,xx
            if col_nome in COLS_VALOR and cell.value not in (None, ''):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right', vertical='center')
            else:
                cell.alignment = Alignment(horizontal='center', vertical='center')

        # Cor condicional na coluna Progresso
        if 'Progresso' in cabec:
            prog_cell = ws.cell(row=r, column=cabec['Progresso'])
            valor = str(prog_cell.value or '').strip()
            if valor == 'Ok' or valor.startswith('Ok -'):
                prog_cell.fill = VERDE
            elif 'VERIFICAR NO SIAFI' in valor:
                prog_cell.fill = LARANJA
            elif valor != '':
                prog_cell.fill = VERMELHO if 'zerado' in valor.lower() or 'maior' in valor.lower() or 'inexistente' in valor.lower() else AMARELO

    # Congela a primeira linha
    ws.freeze_panes = 'A2'

    # Ajusta largura: usa o maior entre o título do cabeçalho e o conteúdo
    for c in range(1, max_col + 1):
        col_letter = get_column_letter(c)
        max_len = 0
        for r in range(1, max_row + 1):
            val = ws.cell(row=r, column=c).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 10), 50)


def formatar_arquivo(caminho):
    """Aplica a formatação visual na conferência já gravada."""
    wb = load_workbook(caminho)
    ws = wb[arquivos.ABA] if arquivos.ABA in wb.sheetnames else wb.active
    formatar_planilha(ws)
    wb.save(caminho)


def formatar_valor(centavos):
    """12345678 -> 'R$ 123.456,78' (o SIAFI recebe o valor em centavos)."""
    inteiros, cents = divmod(int(centavos), 100)
    return f"R$ {inteiros:,}".replace(',', '.') + f",{cents:02d}"


def montar_data_row(valores, unidade_orcamentaria):
    """Converte os valores já validados de uma linha (ver validacao.py) no
    dicionário de textos que os fluxos digitam no SIAFI."""
    natureza = str(valores['Natureza_Despesa_Elemento'])   # 6 dígitos, validado
    return {
        'orientacao': valores['Orientacao'],
        'tipo': valores['Tipo de Descentralizacao'],
        'ue': str(valores['UE_Beneficiada']),
        'fonte': str(valores['Fonte']),
        'procedencia': str(valores['Procedencia']),
        # ATENÇÃO: lido, mas os fluxos ainda NÃO o usam — digitam sempre "n"
        # no campo DEA da tela (ver fluxo_desc.py).
        'dea': valores['Elemento 92'],
        'acao': str(valores['Acao']),
        'iag': str(valores['IAG']),
        'natureza_despesa': natureza,
        'categoria': natureza[:1],
        'grupo': natureza[1:2],
        'modalidade': natureza[2:4],
        'elemento': natureza[4:6],
        # '0' quando a linha não usa o campo (Global / procedência != 2)
        'item': str(valores.get('Item', 0)),
        'uo_financiadora': str(valores.get('UO_Financiadora', 0)),
        # UO da UE executora (vem do .env)
        'unidade_orcamentaria': unidade_orcamentaria,
        'valor': int(round(valores['Valor'] * 100)),   # em centavos
    }


def descrever(data_row):
    """Resumo da linha para a janela do robô."""
    natureza = data_row['natureza_despesa']
    if data_row['tipo'] == 'Amarrado':
        natureza += f".{data_row['item']}"
    return (f"UE = {data_row['ue']}, Tipo = {data_row['tipo']}, "
            f"Fonte e IPU = {data_row['fonte']}.{data_row['procedencia']}, "
            f"UO Financiadora = {data_row['uo_financiadora']}, "
            f"Ação = {data_row['acao']}, Natureza de Despesa = {natureza}, "
            f"Valor = {formatar_valor(data_row['valor'])}")


# ---------------------------------------------------------------------------
# SIAFI
# ---------------------------------------------------------------------------

def _parada_senha_expirada():
    return Parada(
        CODIGO_SENHA_EXPIRADA,
        "Senha do SIAFI expirada.\n"
        "Abra o SIAFI manualmente e atualize sua senha. Depois salve a nova "
        "senha no arquivo .env (campo SENHA) e rode o robô de novo.")


def _parada_login():
    return Parada(
        CODIGO_ERRO,
        "Não foi possível fazer login no SIAFI após várias tentativas.\n"
        "Confira USUARIO e SENHA no arquivo .env e se o SIAFI está no ar.")


def fazer_login(em, cfg):
    """Do formulário de logon até a unidade executora informada."""
    em.fill_field(19, 13, SISTEMA, 8)
    em.fill_field(20, 13, cfg['usuario'], 8)
    em.fill_field(21, 13, cfg['senha'], 8)
    em.send_enter()

    # Checa antes do laço: ele dá Enter antes de ler a tela, o que submeteria
    # a tela de troca de senha em branco e apagaria a mensagem.
    time.sleep(1)
    if senha_expirada(em):
        raise _parada_senha_expirada()

    # Navega pelas telas de aviso até encontrar a mensagem de sucesso
    for tentativa in range(1, 11):
        time.sleep(1)
        try:
            em.send_enter()
            if em.string_found(1, 13, 'Logon executado com sucesso'):
                print("Login realizado com sucesso!")
                break
            if not senha_expirada(em):
                # Tela com campo editável, mas ainda não é a de sucesso
                print(f"Tentativa {tentativa} - tela intermediária, avançando...")
                em.send_enter()
        except Exception:
            # Exception, e não um 'except:' nu, para não engolir o Ctrl+C.
            # Tela SEM campo editável: é a de aviso, só dá Enter e segue.
            print(f"Tentativa {tentativa} - tela de aviso detectada, passando...")
            em.send_enter()

        # Fora do try de propósito: a parada não pode cair no 'except' acima.
        if senha_expirada(em):
            raise _parada_senha_expirada()
    else:
        raise _parada_login()

    em.fill_field(1, 2, SISTEMA, 4)
    em.send_enter()

    # Mesma navegação, agora até a tela que pede a unidade executora
    for tentativa in range(1, 11):
        time.sleep(1)
        try:
            em.send_enter()
            if em.string_found(22, 11, 'Unidade Executora'):
                print("Tela da unidade executora encontrada.")
                break
            print(f"Tentativa {tentativa} - tela intermediária, avançando...")
            em.send_enter()
        except Exception:
            print(f"Tentativa {tentativa} - tela de aviso detectada, passando...")
            em.send_enter()
    else:
        raise _parada_login()

    em.fill_field(22, 30, cfg['unidade_executora'], 7)
    em.send_enter()
    em.wait_for_field()


def ir_para_descentralizacao(em):
    """Do menu principal até o menu de descentralização de cota."""
    # 03 - Movimentação Orçamentária
    em.fill_field(21, 19, '03', 2)
    em.send_enter()
    em.wait_for_field()

    # 03 - Descentralização de Cota Orçamentária
    em.fill_field(21, 19, '03', 2)
    em.send_enter()
    em.wait_for_field()


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def _aviso(*linhas):
    print()
    print('=' * 78)
    for linha in linhas:
        for pedaco in str(linha).split('\n'):
            print(pedaco)
    print('=' * 78)


def _resumir(df):
    """Imprime quantas linhas deram certo, quantas não e quantas faltam."""
    progresso = df['Progresso'].map(lambda v: '' if vazio(v) else str(v).strip())
    ok = int((progresso.eq('Ok') | progresso.str.startswith('Ok -')).sum())
    pendentes = int(progresso.eq('').sum())
    conferir = int(progresso.str.contains('VERIFICAR NO SIAFI', regex=False).sum())
    recusadas = len(df) - ok - pendentes - conferir

    print()
    print(f"Resumo: {ok} linha(s) Ok, {recusadas} não efetivada(s) (veja o "
          f"motivo na coluna Progresso), {conferir} a conferir no SIAFI, "
          f"{pendentes} por fazer.")


def executar(cfg, criar_emulador=Emulator):
    """Processa a conferência pendente. Devolve o código de saída."""
    if not cfg.get('pasta_windows'):
        print('[ERRO] PASTA_WINDOWS não configurada no arquivo .env.')
        return CODIGO_ERRO

    try:
        trava = arquivos.travar_execucao()
    except arquivos.ExecucaoEmAndamento:
        print('Já existe uma execução do robô em andamento. Aguarde ela terminar.')
        return CODIGO_EM_ANDAMENTO
    try:
        return _executar(cfg, criar_emulador)
    finally:
        arquivos.liberar_execucao(trava)


def _executar(cfg, criar_emulador):
    pasta_remanejados = os.path.join(cfg['pasta_windows'], arquivos.SUB_REMANEJADOS)
    pasta_conferencia = os.path.join(cfg['pasta_windows'], arquivos.SUB_CONFERENCIA)
    pasta_local = cfg['pasta_local']
    pasta_em_processamento = os.path.join(pasta_local, arquivos.SUB_EM_PROCESSAMENTO)
    manifesto = os.path.join(pasta_local, arquivos.NOME_MANIFESTO)

    os.makedirs(pasta_em_processamento, exist_ok=True)
    arquivos.recuperar_interrompidas(pasta_em_processamento, pasta_conferencia)

    escolhida = arquivos.conferencia_a_processar(pasta_conferencia)
    if escolhida is None:
        print(f'Nenhuma conferência com linhas pendentes em "{pasta_conferencia}". '
              f'Nada a fazer.')
        return 0

    nome = os.path.basename(escolhida.caminho)
    caminho_local = os.path.join(pasta_em_processamento, nome)
    caminho_destino = os.path.join(pasta_conferencia, nome)

    # A conferência foi gerada pela consolidação desta execução? Só nesse caso
    # dá para desfazer tudo se o robô parar antes de enviar alguma linha.
    conferencia_do_manifesto, _ = arquivos.ler_manifesto(manifesto)
    recem_criada = (conferencia_do_manifesto is not None and
                    os.path.abspath(conferencia_do_manifesto)
                    == os.path.abspath(escolhida.caminho))
    if not recem_criada:
        arquivos.descartar_manifesto(manifesto)   # sobra de outra execução
        print(f"Retomando '{nome}': {escolhida.pendentes} linha(s) por fazer.")

    def desfazer_tudo():
        devolvidos, nao_devolvidos = arquivos.desfazer_consolidacao(
            manifesto, caminho_local)
        planilhas = [os.path.basename(p) for p in devolvidos
                     if os.path.dirname(p) == pasta_remanejados]
        linhas = ['NADA foi enviado ao SIAFI.']
        if planilhas:
            linhas.append(f'As planilhas voltaram para a pasta '
                          f'"{arquivos.SUB_REMANEJADOS}": {", ".join(planilhas)}')
        if nao_devolvidos:
            linhas.append('Não consegui devolver: ' + ', '.join(nao_devolvidos)
                          + ' (procure em "Realizados").')
        linhas.append('Resolva o problema apontado acima e rode o robô de novo.')
        _aviso(*linhas)

    try:
        arquivos.mover(escolhida.caminho, caminho_local)
    except OSError as e:
        # A cópia pode ter ido e o original não ter saído (planilha aberta no
        # Excel). Duas cópias da mesma conferência, uma em cada pasta, fariam
        # as mesmas linhas serem enviadas duas vezes: a local é descartada.
        if os.path.exists(escolhida.caminho) and os.path.exists(caminho_local):
            try:
                os.remove(caminho_local)
            except OSError:
                pass
        _aviso(f"Não consegui tirar '{nome}' da pasta \"{arquivos.SUB_CONFERENCIA}\": {e}",
               'Se a planilha estiver aberta no Excel, feche-a e rode o robô de novo.')
        if recem_criada:
            desfazer_tudo()
        return CODIGO_ERRO

    enviou = False          # alguma linha já foi enviada ao SIAFI nesta execução
    linha_em_curso = None   # índice da linha que está no SIAFI neste momento
    df = None
    em = None
    try:
        df = pd.read_excel(caminho_local, sheet_name=arquivos.ABA)
        df = df.dropna(how='all').reset_index(drop=True)   # remove linhas vazias

        faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
        if faltando:
            raise Parada(CODIGO_ERRO,
                         f"A conferência '{nome}' está sem as colunas: "
                         f"{', '.join(faltando)}.")

        # Garante que a coluna 'Progresso' exista e aceite texto
        if 'Progresso' not in df.columns:
            df['Progresso'] = pd.NA
        df['Progresso'] = df['Progresso'].astype('object')

        problemas = validar_configuracao(cfg)
        if problemas:
            raise Parada(CODIGO_ERRO,
                         'O arquivo .env está incompleto ou incorreto:\n'
                         + '\n'.join(f'  - {p}' for p in problemas))

        # Confere TODAS as linhas pendentes antes do login. Linha com
        # 'Progresso' preenchido já foi tratada numa rodada anterior: pular é
        # o que torna seguro rodar de novo depois de uma interrupção.
        fila = []
        puladas = invalidas = 0
        for idx, row in df.iterrows():
            if not vazio(row['Progresso']):
                puladas += 1
                continue
            valores, erros = validar_linha(row.get)
            if erros:
                df.at[idx, 'Progresso'] = PREFIXO_LINHA_INVALIDA + descrever_erros(erros)
                print(f"Linha {idx + 2}: não será enviada — {df.at[idx, 'Progresso']}")
                invalidas += 1
                continue
            fila.append((idx, montar_data_row(valores, cfg['unidade_orcamentaria'])))

        if invalidas:
            salvar_progresso(df, caminho_local, pasta_local)
        if puladas:
            print(f"{puladas} linha(s) já tratada(s) em execução anterior serão puladas.")
        print(f"{len(fila)} linha(s) a enviar ao SIAFI.")

        if fila:
            try:
                em = conectar_siafi(cfg['host'], cfg['visivel'],
                                    tentativas=cfg['conexao_tentativas'],
                                    criar_emulador=criar_emulador)
            except FalhaDeConexao as e:
                raise Parada(
                    CODIGO_ERRO,
                    f"Não foi possível conectar ao SIAFI após "
                    f"{cfg['conexao_tentativas']} tentativa(s).\n"
                    f"Último motivo: {e}\n"
                    "Verifique se você está na rede do governo ou com a VPN "
                    "ligada, e se o SIAFI está no ar.")

            fazer_login(em, cfg)
            ir_para_descentralizacao(em)

            for idx, data_row in fila:
                operacao = 'anulação' if data_row['orientacao'] == 'Anular' else 'aprovação'
                print(f"Linha {idx + 2}: realizando {operacao} | {descrever(data_row)}")

                if not enviou:
                    # Ponto sem volta: daqui em diante a consolidação não se
                    # desfaz mais, porque já há linha no SIAFI.
                    enviou = True
                    arquivos.descartar_manifesto(manifesto)

                # Marca ANTES de enviar e salva. Se o robô morrer no meio, a
                # linha não fica em branco — em branco ela seria reenviada às
                # cegas, duplicando a operação se ela tiver entrado.
                linha_em_curso = idx
                df.at[idx, 'Progresso'] = PROGRESSO_INCERTO
                salvar_progresso(df, caminho_local, pasta_local)

                if data_row['orientacao'] == 'Anular':
                    retorno, nr_doc = anulacao(em, data_row)
                else:
                    retorno, nr_doc = aprovacao(em, data_row)

                # Troca a marca pelo resultado e salva na hora, para não perder
                # o que já foi feito caso pare mais adiante.
                df.at[idx, 'Progresso'] = traduzir_progresso(retorno, nr_doc)
                salvar_progresso(df, caminho_local, pasta_local)
                linha_em_curso = None

            # Encerra já aqui para a janela do x3270 fechar assim que o SIAFI
            # não é mais necessário. O finally cobre os casos de erro.
            encerrar_emulador(em)
            em = None

        formatar_arquivo(caminho_local)
        arquivos.mover(caminho_local, caminho_destino)
        arquivos.descartar_manifesto(manifesto)
        _resumir(df)
        print(f"Planilha com o resultado em: {caminho_destino}")
        return 0

    except BaseException as e:
        # BaseException (e não Exception) para cobrir também o Ctrl+C: em
        # qualquer saída a planilha já está na pasta local e precisa voltar.
        if isinstance(e, Parada):
            _aviso(e.mensagem)
        elif isinstance(e, KeyboardInterrupt):
            _aviso('Execução interrompida pelo usuário.')
        else:
            _aviso(f'Execução interrompida por erro: {type(e).__name__}: {e}')
            imprimir_tela(em, 'tela no momento do erro')
        encerrar_emulador(em)
        em = None

        if not enviou and recem_criada:
            desfazer_tudo()
        else:
            if linha_em_curso is not None:
                _aviso(f"ATENÇÃO: a linha {linha_em_curso + 2} da conferência parou no meio.",
                       "Não dá para saber se a operação entrou no SIAFI. Confira lá antes de",
                       f"qualquer coisa: ela ficou marcada como '{PROGRESSO_INCERTO}'",
                       "e NÃO será refeita sozinha. Se ela não entrou e você quiser que o robô",
                       "a refaça, apague a coluna Progresso dessa linha e rode de novo.")
            _resgatar(caminho_local, caminho_destino, formatar=enviou)
            if not enviou:
                print('NADA foi enviado ao SIAFI nesta execução.')
            if df is not None and bool(df['Progresso'].map(vazio).any()):
                print('As linhas com a coluna Progresso em branco ainda não foram '
                      'feitas: resolva o problema acima e rode o robô de novo para '
                      'continuar de onde parou.')

        if isinstance(e, Parada):
            return e.codigo
        if isinstance(e, KeyboardInterrupt):
            return CODIGO_INTERROMPIDO
        raise

    finally:
        encerrar_emulador(em)


def _resgatar(caminho_local, caminho_destino, formatar):
    """Devolve a conferência para a pasta "Conferencia" depois de uma falha.

    Sem isso, qualquer erro deixava o arquivo preso na pasta local do WSL: a
    pasta "Conferencia" já estava vazia e as planilhas de entrada já estavam
    em "Realizados", então a execução seguinte não encontrava nada.

    Nunca propaga exceção: roda durante o tratamento de outro erro, e deixar
    uma falha de resgate mascarar o erro original só dificulta o diagnóstico."""
    if not os.path.exists(caminho_local):
        return

    if formatar:
        try:
            formatar_arquivo(caminho_local)
        except Exception as e:
            print(f'[aviso] não foi possível formatar a planilha no resgate: {e}')

    try:
        arquivos.mover(caminho_local, caminho_destino)
        print(f'Conferência devolvida para: {caminho_destino}')
    except Exception as e:
        print(f"[aviso] a conferência ficou em '{caminho_local}' ({e}).")
        print('Ela será devolvida para a pasta "Conferencia" automaticamente na '
              'próxima execução do robô.')


def main():
    return executar(carregar_config())


if __name__ == '__main__':
    sys.exit(main())
