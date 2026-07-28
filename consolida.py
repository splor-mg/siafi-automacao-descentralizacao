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
        └── Conferencia Realizados/              # conferências de dias anteriores

Fluxo:

1. Arquiva a conferência anterior: move o que estiver em "Conferencia" para
   "Realizados/Conferencia Realizados".
2. Lê todas as planilhas de "Remanejados (Insira seu arquivo aqui)", aba
   "Execucao", descarta linhas completamente vazias e VALIDA cada linha.
3. Se qualquer arquivo tiver erro de preenchimento, lista todos os erros
   (planilha, linha do Excel, coluna, valor encontrado) e ABORTA sem gerar
   consolidado — nada é movido, para você poder corrigir e rodar de novo.
4. Não havendo erros, normaliza os campos de texto, concatena, ordena
   "Anular" primeiro e salva o consolidado em "Conferencia" como
   "Conferencia Arquivo Robo DD.MM.xlsx" (acrescentando " (1)", " (2)"...).
5. Move as planilhas de origem para "Realizados/Remanejamento Realizados".

O consolidado é depois lido pelo descentralizacao.py, que o move para a pasta
local de trabalho (PASTA_LINUX), processa no SIAFI e o devolve para "Conferencia".
"""

import os
import shutil
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

# Carrega as configurações do arquivo .env (na raiz do repositório)
load_dotenv()

# ===================== CONFIGURAÇÃO =====================
# Pasta-raiz do projeto no Windows/OneDrive (via /mnt/c). As subpastas abaixo
# são fixas em relação a ela.
PASTA_WINDOWS = os.getenv('PASTA_WINDOWS')

SUB_REMANEJADOS               = 'Remanejados (Insira seu arquivo aqui)'
SUB_CONFERENCIA               = 'Conferencia'
SUB_REALIZADOS_REMANEJAMENTO  = os.path.join('Realizados', 'Remanejamento Realizados')
SUB_REALIZADOS_CONFERENCIA    = os.path.join('Realizados', 'Conferencia Realizados')

ABA_ORIGEM = 'Execucao'
ABA_SAIDA  = 'Execucao'

COLUNAS_ESPERADAS = [
    'Orientacao', 'UE_Beneficiada', 'Tipo de Descentralizacao', 'Fonte',
    'Procedencia', 'Elemento 92', 'Acao', 'IAG', 'Natureza_Despesa_Elemento',
    'Item', 'UO_Financiadora', 'Valor', 'Progresso',
]

# Colunas que precisam existir no arquivo de origem (Progresso é preenchida
# pelo robô depois, então não é obrigatória na entrada).
COLUNAS_OBRIGATORIAS = [
    'Orientacao', 'UE_Beneficiada', 'Tipo de Descentralizacao', 'Fonte',
    'Procedencia', 'Elemento 92', 'Acao', 'IAG', 'Natureza_Despesa_Elemento',
    'Item', 'UO_Financiadora', 'Valor',
]

# Formas canônicas aceitas (chave = valor normalizado p/ minúsculas e sem espaços)
ORIENTACOES_VALIDAS = {'aprovar': 'Aprovar', 'anular': 'Anular'}
TIPOS_VALIDOS       = {'global': 'Global', 'amarrado': 'Amarrado'}
# ========================================================


# ----------------------- Helpers de validação -----------------------

def _inteiro(v):
    """Devolve o valor como int se ele representar um número inteiro
    (aceita 1500002, 1500002.0, '1500002'); caso contrário, None.
    Rejeita texto não numérico, vazios, NaN e booleanos."""
    if pd.isna(v):
        return None
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        try:
            f = float(str(v).strip().replace(',', '.'))
        except (TypeError, ValueError):
            return None
    if not float(f).is_integer():
        return None
    return int(f)


def _numero(v):
    """Devolve float se v for um número (aceita vírgula decimal); senão None."""
    if pd.isna(v):
        return None
    if isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        try:
            return float(str(v).strip().replace(',', '.'))
        except (TypeError, ValueError):
            return None


def _fmt(v):
    """Formata o valor encontrado para a mensagem de erro: vazio/NaN vira
    '(vazio)', números (inclusive tipos do numpy/pandas) saem sem o '.0' e
    textos saem entre aspas para deixar espaços/caracteres visíveis."""
    if pd.isna(v):
        return '(vazio)'
    if isinstance(v, str):
        return repr(v)
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(f)
    except (TypeError, ValueError):
        return repr(v)


def validar_e_normalizar(df, nome_arquivo):
    """Valida cada linha do DataFrame segundo as regras de preenchimento e,
    quando o valor é válido, normaliza os campos de texto (Orientacao, Tipo e
    Elemento 92) para a forma canônica, gravando de volta no próprio df.

    Retorna a lista de erros encontrados (strings prontas para impressão).
    Percorre todas as linhas e colunas — não para no primeiro erro — para que
    o usuário veja tudo o que precisa corrigir de uma vez."""
    erros = []

    for pos in df.index:
        linha = int(df.at[pos, '_linha_excel'])

        def erro(coluna, mensagem, valor):
            erros.append(
                f"{nome_arquivo} | linha {linha} | coluna '{coluna}': "
                f"{mensagem} (encontrado: {_fmt(valor)})"
            )

        # --- Orientacao: "Anular" ou "Aprovar" ---
        v = df.at[pos, 'Orientacao']
        chave = str(v).strip().lower() if pd.notna(v) else ''
        if chave in ORIENTACOES_VALIDAS:
            df.at[pos, 'Orientacao'] = ORIENTACOES_VALIDAS[chave]
        else:
            erro('Orientacao', 'deve ser "Anular" ou "Aprovar"', v)

        # --- Tipo de Descentralizacao: "Amarrado" ou "Global" ---
        v = df.at[pos, 'Tipo de Descentralizacao']
        chave = str(v).strip().lower() if pd.notna(v) else ''
        if chave in TIPOS_VALIDOS:
            tipo = TIPOS_VALIDOS[chave]
            df.at[pos, 'Tipo de Descentralizacao'] = tipo
        else:
            tipo = None
            erro('Tipo de Descentralizacao', 'deve ser "Amarrado" ou "Global"', v)

        # --- UE_Beneficiada: numérica com exatamente 7 dígitos ---
        v = df.at[pos, 'UE_Beneficiada']
        n = _inteiro(v)
        if n is None or not (1000000 <= n <= 9999999):
            erro('UE_Beneficiada', 'deve ser numérica com exatamente 7 dígitos', v)

        # --- Fonte: número de 1 a 99 ---
        v = df.at[pos, 'Fonte']
        n = _inteiro(v)
        if n is None or not (1 <= n <= 99):
            erro('Fonte', 'deve ser um número de 1 a 99', v)

        # --- Procedencia: número de 0 a 9 ---
        v = df.at[pos, 'Procedencia']
        procedencia = _inteiro(v)
        if procedencia is None or not (0 <= procedencia <= 9):
            erro('Procedencia', 'deve ser um número de 0 a 9', v)

        # --- Elemento 92: "S" ou "N" ---
        v = df.at[pos, 'Elemento 92']
        chave = str(v).strip().upper() if pd.notna(v) else ''
        if chave in ('S', 'N'):
            df.at[pos, 'Elemento 92'] = chave
        else:
            erro('Elemento 92', 'deve ser "S" ou "N"', v)

        # --- Acao: numérica com 4 dígitos ---
        v = df.at[pos, 'Acao']
        n = _inteiro(v)
        if n is None or not (1000 <= n <= 9999):
            erro('Acao', 'deve ser numérica com 4 dígitos (ex.: 2500, 9999)', v)

        # --- Natureza_Despesa_Elemento: numérica com 6 dígitos ---
        v = df.at[pos, 'Natureza_Despesa_Elemento']
        n = _inteiro(v)
        if n is None or not (100000 <= n <= 999999):
            erro('Natureza_Despesa_Elemento',
                 'deve ser numérica com 6 dígitos (ex.: 339039, 459052)', v)

        # --- IAG: 0 ou 1 ---
        v = df.at[pos, 'IAG']
        n = _inteiro(v)
        if n is None or n not in (0, 1):
            erro('IAG', 'deve ser 0 ou 1', v)

        # --- Item: número de 1 a 99, obrigatório quando Tipo = "Amarrado" ---
        if tipo == 'Amarrado':
            v = df.at[pos, 'Item']
            n = _inteiro(v)
            if n is None or not (1 <= n <= 99):
                erro('Item',
                     'deve ser um número de 1 a 99 quando o Tipo é "Amarrado"', v)

        # --- UO_Financiadora: numérica com 4 dígitos, obrigatória se Procedencia = 2 ---
        if procedencia == 2:
            v = df.at[pos, 'UO_Financiadora']
            n = _inteiro(v)
            if n is None or not (1000 <= n <= 9999):
                erro('UO_Financiadora',
                     'deve ser numérica com 4 dígitos quando a Procedência é 2 '
                     '(ex.: 1501, 2271)', v)

        # --- Valor: sempre preenchida, com número ---
        v = df.at[pos, 'Valor']
        if pd.isna(v) or (isinstance(v, str) and v.strip() == ''):
            erro('Valor', 'deve ser preenchida', v)
        elif _numero(v) is None:
            erro('Valor', 'deve conter um número', v)

    return erros


# ----------------------- Utilidades de arquivo -----------------------

def _sub(nome: str) -> str:
    """Caminho completo de uma subpasta dentro de PASTA_WINDOWS."""
    return os.path.join(PASTA_WINDOWS, nome)


def listar_xlsx(pasta: str):
    """Lista os .xlsx/.xls de uma pasta, ignorando temporários do Excel (~$)."""
    arquivos = []
    if not os.path.isdir(pasta):
        return arquivos
    for nome in os.listdir(pasta):
        if nome.startswith('~$'):
            continue
        if not nome.lower().endswith(('.xlsx', '.xls')):
            continue
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho):
            arquivos.append(caminho)
    return arquivos


def mover_com_seguranca(origem: str, pasta_destino: str):
    """Move um arquivo para pasta_destino sem sobrescrever (acrescenta (1),
    (2)... em caso de conflito). shutil.move funciona entre filesystems
    diferentes (ex.: /mnt/c <-> Linux), ao contrário de os.replace."""
    os.makedirs(pasta_destino, exist_ok=True)
    destino = os.path.join(pasta_destino, os.path.basename(origem))
    if os.path.exists(destino):
        base, ext = os.path.splitext(os.path.basename(origem))
        i = 1
        while os.path.exists(destino):
            destino = os.path.join(pasta_destino, f'{base} ({i}){ext}')
            i += 1
    shutil.move(origem, destino)


def nome_conferencia_do_dia(pasta: str) -> str:
    """Caminho do arquivo de saída do dia, sem sobrescrever execuções anteriores:
    'Conferencia Arquivo Robo DD.MM.xlsx', depois ' (1)', ' (2)'..."""
    base = f'Conferencia Arquivo Robo {datetime.today().strftime("%d.%m")}'
    destino = os.path.join(pasta, f'{base}.xlsx')
    i = 1
    while os.path.exists(destino):
        destino = os.path.join(pasta, f'{base} ({i}).xlsx')
        i += 1
    return destino


def ler_arquivo_origem(caminho: str):
    """Lê a aba de descentralização, confere se as colunas obrigatórias existem,
    descarta linhas completamente vazias e valida/normaliza o conteúdo.

    Retorna (df_normalizado, erros). Quando há erros, df_normalizado ainda é
    devolvido, mas main() não o utiliza (a consolidação é abortada)."""
    nome = os.path.basename(caminho)
    df = pd.read_excel(caminho, sheet_name=ABA_ORIGEM)
    df.columns = [str(c).strip() for c in df.columns]

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        return None, [f"{nome} | estrutura | colunas obrigatórias ausentes: "
                      f"{', '.join(faltando)}"]

    # Número da linha no Excel (cabeçalho = 1, primeira linha de dados = 2).
    # Calculado antes de descartar qualquer linha, para apontar a posição real.
    df['_linha_excel'] = df.index + 2

    # Remove apenas linhas completamente vazias (ignorando a coluna auxiliar).
    cols_dados = [c for c in df.columns if c != '_linha_excel']
    df = df.dropna(how='all', subset=cols_dados)

    erros = validar_e_normalizar(df, nome)

    # Alinha ao layout padrão (descarta a coluna auxiliar e acrescenta Progresso)
    df = df.reindex(columns=COLUNAS_ESPERADAS)
    return df, erros


def salvar_consolidado(consolidado: pd.DataFrame, destino_final: str):
    """Salva o consolidado de forma atômica (grava em tmp na mesma pasta e
    renomeia)."""
    pasta = os.path.dirname(destino_final)
    os.makedirs(pasta, exist_ok=True)
    caminho_tmp = os.path.join(pasta, '_tmp_consolidado.xlsx')
    with pd.ExcelWriter(caminho_tmp, engine='openpyxl') as writer:
        consolidado.to_excel(writer, sheet_name=ABA_SAIDA, index=False)
    os.replace(caminho_tmp, destino_final)


def main():
    if not PASTA_WINDOWS:
        print('[ERRO] PASTA_WINDOWS não configurada no .env.')
        print('Configure a pasta-raiz "Projeto de Descentralização" e rode novamente.')
        return
    if not os.path.isdir(PASTA_WINDOWS):
        print(f'[ERRO] PASTA_WINDOWS não encontrada: {PASTA_WINDOWS}')
        return

    pasta_remanejados     = _sub(SUB_REMANEJADOS)
    pasta_conferencia     = _sub(SUB_CONFERENCIA)
    pasta_realizados_rem  = _sub(SUB_REALIZADOS_REMANEJAMENTO)
    pasta_realizados_conf = _sub(SUB_REALIZADOS_CONFERENCIA)

    print(f'Projeto: {PASTA_WINDOWS}')

    # -----------------------------------------------------------------
    # 1. Lê e VALIDA todas as planilhas de entrada ANTES de mexer em nada.
    #    (A conferência anterior só é arquivada depois que a validação passa,
    #    para que um erro não deixe o ambiente num estado intermediário.)
    # -----------------------------------------------------------------
    arquivos_origem = listar_xlsx(pasta_remanejados)
    if not arquivos_origem:
        print(f'Nenhuma planilha em "{pasta_remanejados}". Nada a consolidar.')
        return

    blocos = []
    todos_erros = []
    for caminho in arquivos_origem:
        nome = os.path.basename(caminho)
        try:
            df, erros = ler_arquivo_origem(caminho)
        except Exception as e:
            print(f'[ERRO] Falha ao ler {nome}: {e}')
            print('Abortando para não consolidar dados parciais.')
            return

        if erros:
            todos_erros.extend(erros)
            print(f'[X] {nome}: {len(erros)} problema(s) de preenchimento.')
        elif df is not None and not df.empty:
            blocos.append(df)
            print(f'[OK] {nome} ({len(df)} linhas).')
        else:
            print(f'[aviso] {nome}: sem linhas válidas.')

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
        return

    if not blocos:
        print('Nenhuma linha válida encontrada nos arquivos de origem.')
        return

    # -----------------------------------------------------------------
    # 3. Passou na validação: arquiva a conferência anterior.
    # -----------------------------------------------------------------
    anteriores = listar_xlsx(pasta_conferencia)
    for caminho in anteriores:
        mover_com_seguranca(caminho, pasta_realizados_conf)
    if anteriores:
        print(f'{len(anteriores)} conferência(s) anterior(es) movida(s) para: {pasta_realizados_conf}')

    # 4. Consolida e ordena ("Anular" primeiro, demais depois — sort estável)
    consolidado = pd.concat(blocos, ignore_index=True)
    eh_anular = consolidado['Orientacao'].astype(str).str.strip().str.lower() != 'anular'
    consolidado = consolidado.loc[
        eh_anular.sort_values(kind='stable').index
    ].reset_index(drop=True)

    # 5. Salva o consolidado em "Conferencia"
    destino_final = nome_conferencia_do_dia(pasta_conferencia)
    salvar_consolidado(consolidado, destino_final)
    print(f'Consolidado salvo: {destino_final} ({len(consolidado)} linhas no total)')

    # 6. Move as entradas para "Realizados/Remanejamento Realizados"
    for caminho in arquivos_origem:
        mover_com_seguranca(caminho, pasta_realizados_rem)
    print(f'{len(arquivos_origem)} arquivo(s) movido(s) para: {pasta_realizados_rem}')


if __name__ == '__main__':
    main()