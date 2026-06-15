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
   "Execucao", descarta linhas sem UE_Beneficiada e concatena.
3. Ordena "Anular" primeiro, demais depois (sort estável).
4. Salva o consolidado em "Conferencia" como "Conferencia Arquivo Robo DD.MM.xlsx"
   (acrescentando " (1)", " (2)"... se já houver uma execução do mesmo dia).
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
# ========================================================


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


def ler_arquivo_origem(caminho: str) -> pd.DataFrame:
    """Lê a aba de descentralização e alinha as colunas ao layout padrão."""
    df = pd.read_excel(caminho, sheet_name=ABA_ORIGEM)
    df.columns = [str(c).strip() for c in df.columns]

    if 'UE_Beneficiada' not in df.columns:
        raise ValueError(
            f"Coluna 'UE_Beneficiada' não encontrada em {os.path.basename(caminho)}"
        )

    df['UE_Beneficiada'] = pd.to_numeric(df['UE_Beneficiada'], errors='coerce')
    df = df[df['UE_Beneficiada'].notna()].copy()
    df = df.reindex(columns=COLUNAS_ESPERADAS)

    return df


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

    # 1. Arquiva a(s) conferência(s) anterior(es)
    anteriores = listar_xlsx(pasta_conferencia)
    for caminho in anteriores:
        mover_com_seguranca(caminho, pasta_realizados_conf)
    if anteriores:
        print(f'{len(anteriores)} conferência(s) anterior(es) movida(s) para: {pasta_realizados_conf}')

    # 2. Lê as planilhas de entrada
    arquivos_origem = listar_xlsx(pasta_remanejados)
    if not arquivos_origem:
        print(f'Nenhuma planilha em "{pasta_remanejados}". Nada a consolidar.')
        return

    blocos = []
    for caminho in arquivos_origem:
        try:
            df = ler_arquivo_origem(caminho)
            if not df.empty:
                blocos.append(df)
                print(f'Lido: {os.path.basename(caminho)} ({len(df)} linhas)')
            else:
                print(f'[aviso] Sem linhas válidas: {os.path.basename(caminho)}')
        except Exception as e:
            print(f'[ERRO] Falha ao ler {os.path.basename(caminho)}: {e}')
            print('Abortando para não consolidar dados parciais.')
            return

    if not blocos:
        print('Nenhuma linha válida encontrada nos arquivos de origem.')
        return

    # 3. Consolida e ordena ("Anular" primeiro, demais depois — sort estável)
    consolidado = pd.concat(blocos, ignore_index=True)
    eh_anular = consolidado['Orientacao'].astype(str).str.strip().str.lower() != 'anular'
    consolidado = consolidado.loc[
        eh_anular.sort_values(kind='stable').index
    ].reset_index(drop=True)

    # 4. Salva o consolidado em "Conferencia"
    destino_final = nome_conferencia_do_dia(pasta_conferencia)
    salvar_consolidado(consolidado, destino_final)
    print(f'Consolidado salvo: {destino_final} ({len(consolidado)} linhas no total)')

    # 5. Move as entradas para "Realizados/Remanejamento Realizados"
    for caminho in arquivos_origem:
        mover_com_seguranca(caminho, pasta_realizados_rem)
    print(f'{len(arquivos_origem)} arquivo(s) movido(s) para: {pasta_realizados_rem}')


if __name__ == '__main__':
    main()
