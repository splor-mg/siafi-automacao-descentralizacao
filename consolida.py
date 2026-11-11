"""
Consolidação das planilhas de "Descentralização de Cota Orçamentária".

Estrutura de pastas esperada dentro de PASTA_WINDOWS (a pasta-raiz
"Projeto de Descentralização", que muda de computador para computador —
pode estar no OneDrive ou não):

    Projeto de Descentralização/
    ├── Remanejados (Insira seu arquivo aqui)/   # planilhas de entrada
    ├── Conferencia/                             # consolidado gerado fica aqui
    └── Realizados/
        ├── Remanejamento Realizados/            # entradas já consolidadas
        └── Conferencia Realizados/              # conferências anteriores

Fluxo:

0. Arruma o que uma execução anterior tenha deixado pela metade: devolve para
   "Conferencia" a planilha que ficou na pasta local e desfaz a consolidação
   que não chegou a ser executada no SIAFI.
1. Lê todas as planilhas de "Remanejados (Insira seu arquivo aqui)", aba
   "Execucao", ignora linhas vazias e VALIDA cada linha.
2. Se qualquer arquivo tiver erro de preenchimento, lista todos os erros
   (planilha, linha do Excel, coluna, valor encontrado) e ABORTA sem gerar
   consolidado — nada é movido, para você poder corrigir e rodar de novo.
3. Não havendo erros, arquiva a conferência anterior em
   "Realizados/Conferencia Realizados", normaliza os campos, concatena, ordena
   "Anular" primeiro e salva o consolidado em "Conferencia" como
   "Conferencia Arquivo Robo DD.MM.xlsx" (acrescentando " (1)", " (2)"...).
4. Move as planilhas de origem para "Realizados/Remanejamento Realizados".

Os passos 3 e 4 são anotados num manifesto: se algo falhar no meio (planilha
aberta no Excel, por exemplo), tudo volta para o lugar. O descentralizacao.py
usa o mesmo manifesto para desfazer a consolidação quando para antes de enviar
qualquer linha ao SIAFI.

Sem planilha nova na pasta de entrada, a conferência que o robô devolveu
interrompida, com linhas por fazer, é retomada: o código 0 abaixo vale também
para esse caso. Conferência pendente que não veio de uma interrupção do robô
(deixada pela versão anterior, por exemplo) não é executada sozinha.

Antes de tudo, mostra uma vez o aviso da última atualização do robô
(NOVIDADES.txt, ver siafi_automacao/novidades.py).

Códigos de saída (lidos pelo robo.ps1, que só inicia o robô quando o código é 0):

    0  - há conferência pronta para o robô (nova ou retomada).
    1  - erro: configuração ausente, falha de leitura ou erro de preenchimento.
    2  - nada a fazer (pasta "Remanejados" vazia e nenhuma linha pendente).
    10 - já existe outra execução do robô em andamento.
"""

import os
import sys
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'siafi_automacao'))

import arquivos  # noqa: E402
import novidades  # noqa: E402
from validacao import (  # noqa: E402
    COLUNAS_CONFERENCIA, COLUNAS_OBRIGATORIAS, formatar_encontrado,
    validar_linha, vazio,
)

# Aviso mostrado uma vez na janela do robô depois de cada atualização (ver novidades.py)
ARQUIVO_NOVIDADES = os.path.join(BASE_DIR, 'NOVIDADES.txt')

# Planilhas que o robô não lê. O .xls (Excel 97-2003) é erro; os demais são
# só avisados, porque podem ser arquivos de apoio que a pessoa guarda na pasta.
FORMATO_ANTIGO = ('.xls',)
OUTRAS_PLANILHAS = ('.xlsm', '.xlsb', '.ods', '.csv')


# ----------------------- Leitura das entradas -----------------------

def planilhas_em_outro_formato(pasta):
    """Devolve (antigas, outras): nomes dos .xls e das demais planilhas que
    não são .xlsx na pasta de entrada."""
    antigas, outras = [], []
    if os.path.isdir(pasta):
        for nome in sorted(os.listdir(pasta)):
            if nome.startswith('~$'):
                continue
            ext = os.path.splitext(nome)[1].lower()
            if ext in FORMATO_ANTIGO:
                antigas.append(nome)
            elif ext in OUTRAS_PLANILHAS:
                outras.append(nome)
    return antigas, outras


def ler_arquivo_origem(caminho):
    """Lê a aba de descentralização, confere se as colunas obrigatórias
    existem, ignora as linhas vazias e valida/normaliza o conteúdo.

    Devolve (df, erros). 'df' tem o layout da conferência, com os campos
    válidos já na forma canônica; 'erros' são textos prontos para impressão.
    Com erros, a consolidação é abortada e o df não é usado."""
    nome = os.path.basename(caminho)
    try:
        df = pd.read_excel(caminho, sheet_name=arquivos.ABA)
    except PermissionError:
        return None, [f"{nome} | arquivo | não consegui abrir. Se a planilha "
                      f"estiver aberta no Excel, feche-a e rode de novo."]
    except Exception as e:
        if 'Worksheet' in str(e):
            return None, [f"{nome} | arquivo | não tem a aba '{arquivos.ABA}'"]
        return None, [f"{nome} | arquivo | não consegui ler: {e}"]

    df.columns = [str(c).strip() for c in df.columns]

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        return None, [f"{nome} | estrutura | colunas obrigatórias ausentes: "
                      f"{', '.join(faltando)}"]

    linhas = []
    erros = []
    for pos, row in df.iterrows():
        # Linha de dados é a que tem alguma coluna obrigatória preenchida.
        # Anotação solta em outra coluna não vira operação.
        if all(vazio(row[c]) for c in COLUNAS_OBRIGATORIAS):
            continue

        # Número da linha no Excel (cabeçalho = 1, primeira de dados = 2),
        # contado antes de ignorar qualquer linha, para apontar a posição real.
        linha_excel = pos + 2
        valores, erros_linha = validar_linha(row.get)
        for coluna, mensagem, valor in erros_linha:
            erros.append(f"{nome} | linha {linha_excel} | coluna '{coluna}': "
                         f"{mensagem} (encontrado: {formatar_encontrado(valor)})")

        # Campo válido entra na forma canônica; o resto, como estava.
        saida = {c: valores.get(c, row[c]) for c in COLUNAS_OBRIGATORIAS}
        progresso = row.get('Progresso')
        saida['Progresso'] = None if vazio(progresso) else progresso
        linhas.append(saida)

    return pd.DataFrame(linhas, columns=COLUNAS_CONFERENCIA), erros


# ----------------------- Saída -----------------------

def nome_conferencia_do_dia(pasta):
    """Caminho do arquivo de saída do dia, sem sobrescrever execuções anteriores:
    'Conferencia Arquivo Robo DD.MM.xlsx', depois ' (1)', ' (2)'..."""
    return arquivos.destino_livre(
        pasta, f'Conferencia Arquivo Robo {datetime.today().strftime("%d.%m")}.xlsx')


def salvar_consolidado(consolidado, destino_final, pasta_tmp):
    """Grava o consolidado na pasta local e só então o move para o destino.
    Assim a pasta "Conferencia" nunca fica com um arquivo pela metade (um
    temporário esquecido ali seria tratado como conferência)."""
    os.makedirs(pasta_tmp, exist_ok=True)
    os.makedirs(os.path.dirname(destino_final), exist_ok=True)
    caminho_tmp = os.path.join(pasta_tmp, '_tmp_consolidado.xlsx')
    with pd.ExcelWriter(caminho_tmp, engine='openpyxl') as writer:
        consolidado.to_excel(writer, sheet_name=arquivos.ABA, index=False)
    arquivos.mover(caminho_tmp, destino_final)


# ----------------------- Sobras de execução anterior -----------------------

def desfazer_consolidacao_nao_executada(manifesto):
    """Desfaz a consolidação anterior se ela nunca chegou ao SIAFI.

    Acontece quando o robô não chegou a rodar depois da consolidação (janela
    fechada entre uma etapa e outra, por exemplo): as planilhas de entrada já
    estão em "Realizados" e a conferência, sem nenhuma linha feita, está em
    "Conferencia". Devolver as planilhas para a fila deixa tudo como antes e
    permite juntá-las às que chegaram depois.

    O descentralizacao.py apaga o manifesto ao enviar a primeira linha, então
    manifesto + conferência intocada só existe enquanto nada foi enviado.
    """
    conferencia, _movidos = arquivos.ler_manifesto(manifesto)
    if conferencia is None:
        return
    if not os.path.exists(conferencia):
        arquivos.descartar_manifesto(manifesto)
        return

    _pendentes, preenchidas = arquivos.contar_linhas(conferencia)
    if preenchidas:
        arquivos.descartar_manifesto(manifesto)   # já foi ao SIAFI: não se desfaz
        return

    devolvidos, _ = arquivos.desfazer_consolidacao(manifesto)
    if devolvidos:
        print('A consolidação anterior não chegou a ser executada no SIAFI: '
              'foi desfeita e as planilhas voltaram para a fila.')


def sem_planilha_nova(pasta_remanejados, conferencias, permitidas):
    """Pasta de entrada vazia: retoma a conferência que o robô devolveu
    interrompida, se houver ('permitidas', ver arquivos.retomaveis)."""
    retomar = arquivos.escolher_para_processar(conferencias, permitidas=permitidas)
    if retomar is not None:
        print(f'Nenhuma planilha nova em "{pasta_remanejados}".')
        print(f"Retomando a conferência '{os.path.basename(retomar.caminho)}': "
              f"{retomar.pendentes} linha(s) ainda por fazer.")
        return 0

    print(f'Nenhuma planilha em "{pasta_remanejados}". Nada a consolidar.')
    for c in conferencias:
        if not c.pendentes:
            continue
        nome = os.path.basename(c.caminho)
        if os.path.abspath(c.caminho) not in permitidas:
            print(f"[aviso] '{nome}' tem {c.pendentes} linha(s) sem Progresso, "
                  f"mas não foi devolvida assim por uma interrupção do robô e por "
                  f"isso NÃO é executada sozinha: parte dessas linhas pode já estar "
                  f"no SIAFI. Confira no SIAFI e, se ainda precisar delas, "
                  f"coloque-as numa planilha nova.")
        else:
            print(f"[aviso] '{nome}' tem {c.pendentes} linha(s) sem Progresso, "
                  f"mas está parada há {arquivos.dias_parada(c)} dia(s) e por "
                  f"isso NÃO é retomada sozinha (limite: "
                  f"{arquivos.retomada_max_dias()} dias). Se ainda precisar "
                  f"dessas linhas, coloque-as numa planilha nova.")
    return 2


# ----------------------- Fluxo principal -----------------------

def consolidar(pasta_windows, pasta_local):
    """Consolida as planilhas de entrada. Devolve o código de saída."""
    print(f'Projeto: {pasta_windows}')

    try:
        trava = arquivos.travar_execucao()
    except arquivos.ExecucaoEmAndamento:
        print('Já existe uma execução do robô em andamento. Aguarde ela terminar.')
        return 10
    try:
        return _consolidar(pasta_windows, pasta_local)
    finally:
        arquivos.liberar_execucao(trava)


def _consolidar(pasta_windows, pasta_local):
    pasta_remanejados     = os.path.join(pasta_windows, arquivos.SUB_REMANEJADOS)
    pasta_conferencia     = os.path.join(pasta_windows, arquivos.SUB_CONFERENCIA)
    pasta_realizados_rem  = os.path.join(pasta_windows, arquivos.SUB_REALIZADOS_REMANEJAMENTO)
    pasta_realizados_conf = os.path.join(pasta_windows, arquivos.SUB_REALIZADOS_CONFERENCIA)
    pasta_em_processamento = os.path.join(pasta_local, arquivos.SUB_EM_PROCESSAMENTO)
    manifesto = os.path.join(pasta_local, arquivos.NOME_MANIFESTO)
    registro = os.path.join(pasta_local, arquivos.NOME_RETOMAVEIS)

    # -----------------------------------------------------------------
    # 0. Arruma o que uma execução anterior deixou pela metade.
    # -----------------------------------------------------------------
    arquivos.recuperar_interrompidas(pasta_em_processamento, pasta_conferencia, registro)
    desfazer_consolidacao_nao_executada(manifesto)

    # -----------------------------------------------------------------
    # 1. Lê e VALIDA todas as planilhas de entrada ANTES de mexer em nada.
    #    (A conferência anterior só é arquivada depois que a validação passa,
    #    para que um erro não deixe o ambiente num estado intermediário.)
    # -----------------------------------------------------------------
    arquivos_origem = arquivos.listar_xlsx(pasta_remanejados)
    antigas, outras = planilhas_em_outro_formato(pasta_remanejados)
    for nome in outras:
        print(f"[aviso] '{nome}' não é .xlsx e foi ignorado.")

    if not arquivos_origem and not antigas:
        return sem_planilha_nova(pasta_remanejados,
                                 arquivos.listar_conferencias(pasta_conferencia),
                                 arquivos.retomaveis(registro))

    blocos = []
    todos_erros = [
        f"{nome} | arquivo | está no formato antigo do Excel (.xls). Abra a "
        f"planilha e use Salvar como > Pasta de Trabalho do Excel (.xlsx)."
        for nome in antigas
    ]
    for caminho in arquivos_origem:
        nome = os.path.basename(caminho)
        df, erros = ler_arquivo_origem(caminho)

        if erros:
            todos_erros.extend(erros)
            print(f'[X] {nome}: {len(erros)} problema(s).')
        elif not df.empty:
            blocos.append(df)
            print(f'[OK] {nome} ({len(df)} linhas).')
        else:
            print(f'[aviso] {nome}: sem linhas preenchidas.')

    # -----------------------------------------------------------------
    # 2. Havendo qualquer erro, lista tudo e ABORTA (nada foi movido/gerado).
    # -----------------------------------------------------------------
    if todos_erros:
        print()
        print('=' * 78)
        print(f'VALIDAÇÃO ENCONTROU {len(todos_erros)} PROBLEMA(S). Nada foi consolidado.')
        print('Corrija os itens abaixo nas planilhas de origem e rode novamente:')
        print('=' * 78)
        for e in todos_erros:
            print(f'  - {e}')
        print('=' * 78)
        return 1

    if not blocos:
        print('Nenhuma linha preenchida encontrada nos arquivos de origem.')
        return 2

    # Consolida e ordena ("Anular" primeiro, demais depois — sort estável)
    consolidado = pd.concat(blocos, ignore_index=True)
    nao_e_anular = consolidado['Orientacao'].astype(str).str.strip().str.lower() != 'anular'
    consolidado = consolidado.loc[
        nao_e_anular.sort_values(kind='stable').index
    ].reset_index(drop=True)

    # -----------------------------------------------------------------
    # 3 e 4. Passou na validação: arquiva a conferência anterior, salva a nova
    #        e tira as entradas da fila. Cada passo é anotado no manifesto; se
    #        qualquer um falhar, tudo é desfeito.
    # -----------------------------------------------------------------
    arquivos.iniciar_manifesto(manifesto)
    try:
        anteriores = arquivos.listar_conferencias(pasta_conferencia)
        for c in anteriores:
            destino = arquivos.mover_para_pasta(c.caminho, pasta_realizados_conf)
            arquivos.registrar_movido(manifesto, destino, c.caminho)
            if c.pendentes:
                # Chegou planilha nova: a conferência antiga não é retomada,
                # mas o que ficou sem fazer nela não pode sumir em silêncio.
                print(f"[ATENÇÃO] a conferência anterior "
                      f"'{os.path.basename(c.caminho)}' tinha {c.pendentes} "
                      f"linha(s) sem Progresso, que NÃO foram executadas. Ela "
                      f"foi arquivada em: {destino}")
                print("          Se ainda precisar dessas linhas, coloque-as "
                      "numa planilha nova.")
        if anteriores:
            print(f'{len(anteriores)} conferência(s) anterior(es) movida(s) para: {pasta_realizados_conf}')

        destino_final = nome_conferencia_do_dia(pasta_conferencia)
        arquivos.registrar_conferencia(manifesto, destino_final)
        salvar_consolidado(consolidado, destino_final, pasta_local)
        print(f'Consolidado salvo: {destino_final} ({len(consolidado)} linhas no total)')

        for caminho in arquivos_origem:
            destino = arquivos.mover_para_pasta(caminho, pasta_realizados_rem)
            arquivos.registrar_movido(manifesto, destino, caminho)
        print(f'{len(arquivos_origem)} arquivo(s) movido(s) para: {pasta_realizados_rem}')

    except BaseException as e:
        # BaseException para cobrir também o Ctrl+C: parar aqui deixaria parte
        # das planilhas em "Realizados" sem nunca terem sido executadas.
        print()
        print(f'[ERRO] Não consegui concluir a consolidação: {type(e).__name__}: {e}')
        print('Se alguma planilha estiver aberta no Excel, feche-a e rode de novo.')
        arquivos.desfazer_consolidacao(manifesto)
        print('Nada foi consolidado: as planilhas continuam na pasta de entrada.')
        if isinstance(e, Exception):
            return 1
        raise

    return 0


def main():
    # utf-8-sig: o Bloco de Notas do Windows pode gravar um BOM no .env.
    load_dotenv(os.path.join(BASE_DIR, '.env'), encoding='utf-8-sig')
    pasta_windows = os.getenv('PASTA_WINDOWS')
    pasta_local = os.getenv('PASTA_LINUX') or os.path.join(BASE_DIR, 'data')

    # Primeira coisa da janela: o consolida.py é o primeiro passo depois do
    # git pull em qualquer versão do lançador.
    try:
        novidades.mostrar(ARQUIVO_NOVIDADES,
                          os.path.join(pasta_local, novidades.NOME_MARCADOR))
    except Exception as e:
        print(f'[aviso] não consegui mostrar o aviso de atualização: {e}')

    if not pasta_windows:
        print('[ERRO] PASTA_WINDOWS não configurada no .env.')
        print('Configure a pasta-raiz "Projeto de Descentralização" e rode novamente.')
        return 1
    if not os.path.isdir(pasta_windows):
        print(f'[ERRO] PASTA_WINDOWS não encontrada: {pasta_windows}')
        return 1

    return consolidar(pasta_windows, pasta_local)


if __name__ == '__main__':
    sys.exit(main())
