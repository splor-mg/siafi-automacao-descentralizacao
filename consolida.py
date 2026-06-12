"""
Consolidação das planilhas de "Descentralização de Cota Orçamentária".

Fluxo:

1. Procura todos os arquivos .xlsx/.xls na pasta DATA (ignora ~$ e o próprio
   consolidado.xlsx).

2. Lê a aba "Descentraliza Cota Orçamentaria" de cada arquivo, descarta linhas
   sem UE_Beneficiada e concatena tudo.

3. Ordena o resultado colocando primeiro as linhas com Orientacao == "Anular"
   e depois as demais (ex.: "Aprovar"), preservando a ordem original dentro
   de cada grupo.

4. Salva o consolidado em DATA com o nome "consolidado.xlsx".

5. Move os arquivos de origem para a subpasta DATA/Realizados.
"""

import os

import pandas as pd

# ===================== CONFIGURAÇÃO =====================
DATA = '/home/guilhermemelof/code/splor-mg/siafi-automacao-descentralizacao/data'

REALIZADOS = os.path.join(DATA, 'Realizados')

ABA_ORIGEM    = 'Descentraliza Cota Orçamentaria'
ABA_SAIDA     = 'Descentraliza Cota Orçamentaria'
NOME_SAIDA    = 'consolidado.xlsx'

COLUNAS_ESPERADAS = [
    'Orientacao', 'UE_Beneficiada', 'Tipo de Descentralizacao', 'Fonte',
    'Procedencia', 'Elemento 92', 'Acao', 'Natureza_Despesa_Elemento',
    'Item', 'UO_Financiadora', 'Valor', 'Progresso', 'IAG',
]
# ========================================================


def listar_arquivos_origem(pasta: str):
    arquivos = []
    for nome in os.listdir(pasta):
        if nome.startswith('~$'):
            continue
        if not nome.lower().endswith(('.xlsx', '.xls')):
            continue
        if nome == NOME_SAIDA:
            continue
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho):
            arquivos.append(caminho)
    return arquivos


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


def mover_com_seguranca(origem: str, pasta_destino: str):
    os.makedirs(pasta_destino, exist_ok=True)
    destino = os.path.join(pasta_destino, os.path.basename(origem))
    if os.path.exists(destino):
        base, ext = os.path.splitext(os.path.basename(origem))
        i = 1
        while os.path.exists(destino):
            destino = os.path.join(pasta_destino, f'{base} ({i}){ext}')
            i += 1
    os.replace(origem, destino)


def main():
    print(f'Pasta de dados: {DATA}')

    arquivos_origem = listar_arquivos_origem(DATA)
    if not arquivos_origem:
        print('Nenhum arquivo encontrado na pasta data. Nada a consolidar.')
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

    consolidado = pd.concat(blocos, ignore_index=True)

    # Ordena: linhas "Anular" primeiro, demais depois, preservando a ordem
    # original dentro de cada grupo (sort estável).
    eh_anular = consolidado['Orientacao'].astype(str).str.strip().str.lower() != 'anular'
    consolidado = consolidado.loc[
        eh_anular.sort_values(kind='stable').index
    ].reset_index(drop=True)

    # Salva o consolidado em DATA
    destino_final = os.path.join(DATA, NOME_SAIDA)
    caminho_tmp = os.path.join(DATA, '_tmp_consolidado.xlsx')

    with pd.ExcelWriter(caminho_tmp, engine='openpyxl') as writer:
        consolidado.to_excel(writer, sheet_name=ABA_SAIDA, index=False)

    os.replace(caminho_tmp, destino_final)
    print(f'Salvo: {destino_final} ({len(consolidado)} linhas no total)')

    # Move os arquivos de origem para Realizados
    for caminho in arquivos_origem:
        mover_com_seguranca(caminho, REALIZADOS)
    print(f'{len(arquivos_origem)} arquivo(s) movidos para: {REALIZADOS}')


if __name__ == '__main__':
    main()