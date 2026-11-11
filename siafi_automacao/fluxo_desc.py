"""Lançamento de uma linha de descentralização no terminal do SIAFI.

A aprovação e a anulação passam pelas MESMAS telas, com os mesmos campos nas
mesmas posições. O que muda é a opção do menu e a lista de mensagens com que o
SIAFI recusa cada uma — e é só isso que fluxo_aprovar_desc.py e
fluxo_anular_desc.py informam. Antes cada um repetia este arquivo inteiro, e
toda correção precisava ser feita duas vezes.

As telas são manipuladas por coordenadas fixas (linha, coluna). Mudança de
layout no SIAFI quebra essas coordenadas.
"""

import time

from emulador import MSG_INCONSISTENCIA, esperar_teclado, numero_apos, tela_contem

MSG_NAO_CONFIRMADA = '0017-TECLE PF5 PARA CONFIRMAR OU PF2 PARA ANULAR.'

JUSTIFICATIVA = 'Remanejamento realizado conforme solicitado'


def _preencher_classificacao(em, data_row):
    """Primeira tela: o que está sendo descentralizado e para quem."""
    if data_row['tipo'] == 'Global':
        em.fill_field(10, 53, 'x', 1)   # global
    elif data_row['tipo'] == 'Amarrado':
        em.fill_field(11, 53, 'x', 1)   # amarrado
    else:
        return

    em.fill_field(12, 53, data_row['unidade_orcamentaria'], 4)   # UO
    em.fill_field(13, 53, data_row['iag'], 1)                    # IAG
    em.fill_field(13, 63, f"{data_row['fonte']}{data_row['procedencia']}", 3)  # fonte e procedência
    em.fill_field(14, 53, 'n', 1)                                # DEA (elemento 92): sempre "não"
    em.fill_field(15, 53, data_row['ue'], 7)                     # UE beneficiada
    em.fill_field(17, 46, data_row['acao'], 4)                   # ação
    em.fill_field(17, 51, '0001', 4)
    em.fill_field(18, 46, data_row['categoria'], 1)              # categoria
    em.fill_field(18, 48, data_row['grupo'], 1)                  # grupo
    em.fill_field(18, 50, data_row['modalidade'], 2)             # modalidade
    em.fill_field(18, 53, data_row['elemento'], 2)               # elemento
    if data_row['tipo'] == 'Amarrado':
        em.fill_field(19, 46, data_row['item'], 2)               # item
    if data_row['procedencia'] == '2':
        em.fill_field(20, 46, data_row['uo_financiadora'], 4)    # UO financiadora
    em.send_enter()
    em.wait_for_field()


def _lancar(em, data_row, recusas_classificacao, recusas_valor):
    """Preenche as telas e confirma. Devolve (retorno, nr_doc).

    As recusas casam pelo COMEÇO da mensagem: algumas trazem um complemento
    que varia (a conta, no 'E90 - SALDO ZERADO NA CONTA ...')."""
    _preencher_classificacao(em, data_row)

    retorno = em.string_get(1, 1, 80).strip()
    if retorno.startswith(recusas_classificacao):
        # Não segue para a tela de valor: digitaria na tela errada.
        return retorno, ''

    time.sleep(1)
    # O SIAFI às vezes volta a travar o teclado depois do wait_for_field().
    esperar_teclado(em)
    em.fill_field(17, 63, str(data_row['valor']), 15)   # valor, em centavos
    time.sleep(1)
    em.send_enter()
    em.wait_for_field()

    retorno = em.string_get(1, 1, 80).strip()
    if retorno.startswith(recusas_valor):
        return retorno, ''

    time.sleep(1)
    em.fill_field(11, 11, JUSTIFICATIVA, 60)
    em.send_enter()
    em.wait_for_field()
    # Até aqui nada foi gravado. Do PF5 em diante o SIAFI pode ter registrado
    # a operação, mesmo que o robô quebre antes de ler a resposta.
    em.send_pf(5)
    em.wait_for_field()
    em.send_pf(5)
    em.wait_for_field()

    nr_doc = numero_apos(em.string_get(7, 1, 80).strip(), 'Nr. Documento Global:')
    time.sleep(1)

    retorno = em.string_get(1, 1, 80).strip()
    if retorno == MSG_NAO_CONFIRMADA and tela_contem(em, MSG_INCONSISTENCIA):
        # O PF5 não confirmou: o SIAFI abriu por cima a janela de
        # inconsistência contábil, que é o motivo de verdade.
        retorno = MSG_INCONSISTENCIA
    return retorno, nr_doc


def lancar(em, data_row, opcao_menu, recusas_classificacao, recusas_valor):
    """Entra na opção do menu, lança a linha e volta ao menu.

    Devolve (retorno, nr_doc): a mensagem da linha 1 do SIAFI ao final e o
    número do documento global, que só vem preenchido quando a operação é
    efetivada.
    """
    em.fill_field(21, 19, opcao_menu, 2)
    em.fill_field(21, 41, '1', 1)
    em.send_enter()
    em.wait_for_field()

    retorno, nr_doc = _lancar(em, data_row, recusas_classificacao, recusas_valor)

    print(f"SIAFI retornou: {retorno}")
    em.send_pf(3)
    em.wait_for_field()

    return retorno, nr_doc
