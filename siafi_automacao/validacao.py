"""Regras de preenchimento de uma linha da planilha de descentralização.

A MESMA regra é aplicada duas vezes, de propósito:

  - pelo consolida.py, em todas as planilhas de entrada, antes de mover
    qualquer arquivo;
  - pelo descentralizacao.py, em cada linha pendente, antes do login no SIAFI.
    A conferência pode ter sido editada à mão entre uma execução e outra, e
    uma célula inválida descoberta no meio do laço derrubava o robô com o
    SIAFI já aberto e parte das linhas feitas.

Funções puras, sem SIAFI e sem arquivo, para serem testáveis.
"""

import re

import pandas as pd

# Colunas que precisam existir no arquivo de origem. 'Progresso' é preenchida
# pelo robô depois, então não é obrigatória na entrada.
COLUNAS_OBRIGATORIAS = [
    'Orientacao', 'UE_Beneficiada', 'Tipo de Descentralizacao', 'Fonte',
    'Procedencia', 'Elemento 92', 'Acao', 'IAG', 'Natureza_Despesa_Elemento',
    'Item', 'UO_Financiadora', 'Valor',
]
COLUNAS_CONFERENCIA = COLUNAS_OBRIGATORIAS + ['Progresso']

# Formas canônicas aceitas (chave = valor em minúsculas e sem espaços)
ORIENTACOES_VALIDAS = {'aprovar': 'Aprovar', 'anular': 'Anular'}
TIPOS_VALIDOS = {'global': 'Global', 'amarrado': 'Amarrado'}

# Valor digitado como TEXTO: só é aceito nos formatos sem ambiguidade.
#   1500 | 1500,5 | 1500.50      -> um único separador, com 1 ou 2 decimais
#   1.500,00 | 12.345.678,9      -> milhar com ponto e decimal com vírgula
# '1.500' fica de fora de propósito: em português é mil e quinhentos, mas o
# float() do Python lê um e meio — e o robô enviaria R$ 1,50 ao SIAFI.
_VALOR_SIMPLES = re.compile(r'^\d+([.,]\d{1,2})?$')
_VALOR_COM_MILHAR = re.compile(r'^\d{1,3}(\.\d{3})+,\d{1,2}$')


def vazio(v):
    """True para célula vazia: None, NaN ou texto em branco."""
    if isinstance(v, str):
        return v.strip() == ''
    return bool(pd.isna(v))


def inteiro(v):
    """Devolve o valor como int se ele representar um número inteiro
    (aceita 1500002, 1500002.0, '1500002'); caso contrário, None.
    Rejeita texto não numérico, vazios, NaN e booleanos."""
    if vazio(v) or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        try:
            f = float(str(v).strip().replace(',', '.'))
        except (TypeError, ValueError):
            return None
    if not f.is_integer():
        return None
    return int(f)


def numero(v):
    """Devolve float se v for um valor monetário reconhecível; senão None.

    Célula numérica do Excel é aceita como está. Texto só é aceito nos
    formatos sem ambiguidade (ver _VALOR_SIMPLES e _VALOR_COM_MILHAR)."""
    if vazio(v) or isinstance(v, bool):
        return None
    if isinstance(v, str):
        texto = v.strip()
        if _VALOR_COM_MILHAR.match(texto):
            return float(texto.replace('.', '').replace(',', '.'))
        if _VALOR_SIMPLES.match(texto):
            return float(texto.replace(',', '.'))
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    # inf e nan passam pelo float(), mas não são valores
    return f if f == f and f not in (float('inf'), float('-inf')) else None


def formatar_encontrado(v):
    """Formata o valor encontrado para a mensagem de erro: vazio/NaN vira
    '(vazio)', números (inclusive tipos do numpy/pandas) saem sem o '.0' e
    textos saem entre aspas para deixar espaços/caracteres visíveis."""
    if vazio(v):
        return '(vazio)'
    if isinstance(v, str):
        return repr(v)
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(f)
    except (TypeError, ValueError):
        return repr(v)


def validar_linha(get):
    """Valida uma linha e devolve (valores, erros).

    'get' recebe o nome da coluna e devolve o valor cru da célula.

    'valores' traz cada campo VÁLIDO já na forma canônica (textos
    padronizados, códigos como int, Valor como float). 'Item' e
    'UO_Financiadora' só entram quando a linha os exige — fora disso o robô
    não os digita, então o que estiver na célula é ignorado.

    'erros' é uma lista de (coluna, mensagem, valor_encontrado). Percorre
    todas as colunas, sem parar no primeiro erro, para a pessoa ver de uma vez
    tudo o que precisa corrigir."""
    valores = {}
    erros = []

    def erro(coluna, mensagem):
        erros.append((coluna, mensagem, get(coluna)))

    # --- Orientacao: "Anular" ou "Aprovar" ---
    v = get('Orientacao')
    chave = '' if vazio(v) else str(v).strip().lower()
    if chave in ORIENTACOES_VALIDAS:
        valores['Orientacao'] = ORIENTACOES_VALIDAS[chave]
    else:
        erro('Orientacao', 'deve ser "Anular" ou "Aprovar"')

    # --- Tipo de Descentralizacao: "Amarrado" ou "Global" ---
    v = get('Tipo de Descentralizacao')
    chave = '' if vazio(v) else str(v).strip().lower()
    tipo = TIPOS_VALIDOS.get(chave)
    if tipo:
        valores['Tipo de Descentralizacao'] = tipo
    else:
        erro('Tipo de Descentralizacao', 'deve ser "Amarrado" ou "Global"')

    # --- UE_Beneficiada: numérica com exatamente 7 dígitos ---
    n = inteiro(get('UE_Beneficiada'))
    if n is not None and 1000000 <= n <= 9999999:
        valores['UE_Beneficiada'] = n
    else:
        erro('UE_Beneficiada', 'deve ser numérica com exatamente 7 dígitos')

    # --- Fonte: número de 1 a 99 ---
    n = inteiro(get('Fonte'))
    if n is not None and 1 <= n <= 99:
        valores['Fonte'] = n
    else:
        erro('Fonte', 'deve ser um número de 1 a 99')

    # --- Procedencia: número de 0 a 9 ---
    procedencia = inteiro(get('Procedencia'))
    if procedencia is not None and 0 <= procedencia <= 9:
        valores['Procedencia'] = procedencia
    else:
        procedencia = None
        erro('Procedencia', 'deve ser um número de 0 a 9')

    # --- Elemento 92: "S" ou "N" ---
    v = get('Elemento 92')
    chave = '' if vazio(v) else str(v).strip().upper()
    if chave in ('S', 'N'):
        valores['Elemento 92'] = chave
    else:
        erro('Elemento 92', 'deve ser "S" ou "N"')

    # --- Acao: numérica com 4 dígitos ---
    n = inteiro(get('Acao'))
    if n is not None and 1000 <= n <= 9999:
        valores['Acao'] = n
    else:
        erro('Acao', 'deve ser numérica com 4 dígitos (ex.: 2500, 9999)')

    # --- Natureza_Despesa_Elemento: numérica com 6 dígitos ---
    n = inteiro(get('Natureza_Despesa_Elemento'))
    if n is not None and 100000 <= n <= 999999:
        valores['Natureza_Despesa_Elemento'] = n
    else:
        erro('Natureza_Despesa_Elemento',
             'deve ser numérica com 6 dígitos (ex.: 339039, 459052)')

    # --- IAG: 0 ou 1 ---
    n = inteiro(get('IAG'))
    if n in (0, 1):
        valores['IAG'] = n
    else:
        erro('IAG', 'deve ser 0 ou 1')

    # --- Item: número de 1 a 99, obrigatório quando Tipo = "Amarrado" ---
    if tipo == 'Amarrado':
        n = inteiro(get('Item'))
        if n is not None and 1 <= n <= 99:
            valores['Item'] = n
        else:
            erro('Item',
                 'deve ser um número de 1 a 99 quando o Tipo é "Amarrado"')

    # --- UO_Financiadora: 4 dígitos, obrigatória se Procedencia = 2 ---
    if procedencia == 2:
        n = inteiro(get('UO_Financiadora'))
        if n is not None and 1000 <= n <= 9999:
            valores['UO_Financiadora'] = n
        else:
            erro('UO_Financiadora',
                 'deve ser numérica com 4 dígitos quando a Procedência é 2 '
                 '(ex.: 1501, 2271)')

    # --- Valor: sempre preenchido, numérico e maior que zero ---
    v = get('Valor')
    if vazio(v):
        erro('Valor', 'deve ser preenchida')
    else:
        n = numero(v)
        if n is None:
            erro('Valor',
                 'deve conter um número (se estiver como texto, use 1500,50 '
                 'ou 1.500,50)')
        elif n <= 0:
            # O sentido da operação vem da coluna Orientacao, nunca do sinal.
            erro('Valor', 'deve ser maior que zero')
        else:
            valores['Valor'] = n

    return valores, erros


def descrever_erros(erros):
    """Frase curta com os problemas de UMA linha, para a coluna Progresso."""
    return '; '.join(
        f"{coluna} {mensagem} (encontrado: {formatar_encontrado(valor)})"
        for coluna, mensagem, valor in erros
    )
