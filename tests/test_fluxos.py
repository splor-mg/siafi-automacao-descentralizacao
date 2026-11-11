"""O que os fluxos digitam no SIAFI, tecla a tecla.

As telas são preenchidas por coordenadas fixas. Estes testes travam a
sequência exata: qualquer mudança nela precisa ser deliberada, porque não há
como testar contra o mainframe antes de rodar em produção.
"""
import pytest
from py3270 import CommandError

from fluxo_anular_desc import anulacao
from fluxo_aprovar_desc import aprovacao
from fluxo_desc import MSG_INCONSISTENCIA
from tests.emulador_falso import (MSG_CONFIRMAR, MSG_REGISTRO, VAZIA,
                                  EmuladorFalso, roteiro_linha_ok,
                                  roteiro_linha_recusada_na_classificacao)

ENTER = ('send_enter',)


def data_row(tipo='Global', procedencia='1'):
    return {
        'orientacao': 'Aprovar', 'tipo': tipo, 'ue': '1500008', 'fonte': '10',
        'procedencia': procedencia, 'dea': 'N', 'acao': '2500', 'iag': '0',
        'natureza_despesa': '339039', 'categoria': '3', 'grupo': '3',
        'modalidade': '90', 'elemento': '39', 'item': '5',
        'uo_financiadora': '2271', 'unidade_orcamentaria': '1501',
        'valor': 150050,
    }


def test_aprovacao_global_digita_exatamente_isto():
    em = EmuladorFalso(roteiro_linha_ok('2026000123'))

    retorno, nr_doc = aprovacao(em, data_row('Global'))

    assert (retorno, nr_doc) == (MSG_REGISTRO, '2026000123')
    assert em.digitado() == [
        ('fill_field', 21, 19, '01', 2),        # opção 01: aprovação
        ('fill_field', 21, 41, '1', 1),
        ENTER,
        ('fill_field', 10, 53, 'x', 1),         # global
        ('fill_field', 12, 53, '1501', 4),      # UO
        ('fill_field', 13, 53, '0', 1),         # IAG
        ('fill_field', 13, 63, '101', 3),       # fonte + procedência
        ('fill_field', 14, 53, 'n', 1),         # DEA
        ('fill_field', 15, 53, '1500008', 7),   # UE beneficiada
        ('fill_field', 17, 46, '2500', 4),      # ação
        ('fill_field', 17, 51, '0001', 4),
        ('fill_field', 18, 46, '3', 1),         # categoria
        ('fill_field', 18, 48, '3', 1),         # grupo
        ('fill_field', 18, 50, '90', 2),        # modalidade
        ('fill_field', 18, 53, '39', 2),        # elemento
        ENTER,
        ('fill_field', 17, 63, '150050', 15),   # valor em centavos
        ENTER,
        ('fill_field', 11, 11, 'Remanejamento realizado conforme solicitado', 60),
        ENTER,
        ('send_pf', 5),
        ('send_pf', 5),
        ('send_pf', 3),
    ]


def test_anulacao_amarrada_com_procedencia_2_muda_so_o_que_deve():
    """Em relação à aprovação global: opção 02, o 'x' na linha do amarrado, o
    item e a UO financiadora."""
    em_ref = EmuladorFalso(roteiro_linha_ok())
    aprovacao(em_ref, data_row('Global'))
    em = EmuladorFalso(roteiro_linha_ok())

    anulacao(em, data_row('Amarrado', procedencia='2'))

    so_no_amarrado = [c for c in em.digitado() if c not in em_ref.digitado()]
    assert so_no_amarrado == [
        ('fill_field', 21, 19, '02', 2),        # opção 02: anulação
        ('fill_field', 11, 53, 'x', 1),         # amarrado
        ('fill_field', 13, 63, '102', 3),       # fonte + procedência 2
        ('fill_field', 19, 46, '5', 2),         # item
        ('fill_field', 20, 46, '2271', 4),      # UO financiadora
    ]
    assert ('fill_field', 10, 53, 'x', 1) not in em.digitado()


def test_espera_o_teclado_destravar_antes_de_digitar_o_valor():
    em = EmuladorFalso(roteiro_linha_ok())

    aprovacao(em, data_row())

    posicao_espera = em.chamadas.index(('exec_command', b'Wait(10, Unlock)'))
    posicao_valor = em.chamadas.index(('fill_field', 17, 63, '150050', 15))
    assert posicao_espera < posicao_valor


def test_teclado_que_nao_destrava_nao_derruba_o_fluxo_na_espera():
    """Quem deve falhar, com mensagem clara, é o fill_field seguinte."""
    class TecladoPreso(EmuladorFalso):
        def exec_command(self, comando):
            raise CommandError('Keyboard locked')

    em = TecladoPreso(roteiro_linha_ok())

    assert aprovacao(em, data_row())[0] == MSG_REGISTRO


@pytest.mark.parametrize('mensagem', [
    'E90 - SALDO ZERADO NA CONTA 6.2.2.1.1.01.01',     # o final varia
    '0139- PROJ/ATIV OU FONTE/PROC./IAG INEXISTENTE PARA UO',
    '0101- NATUREZA DESPESA INEXISTENTE(S).',
])
def test_recusa_na_primeira_tela_nao_digita_o_valor(mensagem):
    em = EmuladorFalso(roteiro_linha_recusada_na_classificacao(mensagem))

    retorno, nr_doc = aprovacao(em, data_row())

    assert (retorno, nr_doc) == (mensagem, '')
    assert ('fill_field', 17, 63, '150050', 15) not in em.digitado()
    assert em.digitado()[-1] == ('send_pf', 3)      # voltou ao menu
    assert ('send_pf', 5) not in em.digitado()      # nada foi confirmado


def test_recusa_depois_do_valor_nao_confirma():
    mensagem = '0139- VALOR A DESCENTRALIZAR MAIOR QUE SALDO APROVADO.'
    em = EmuladorFalso([VAZIA, VAZIA, {1: mensagem}, VAZIA])

    retorno, nr_doc = aprovacao(em, data_row())

    assert (retorno, nr_doc) == (mensagem, '')
    assert ('send_pf', 5) not in em.digitado()


def test_recusa_propria_da_anulacao_so_para_a_anulacao():
    mensagem = '0139- SALDO INEXISTENTE A ANULAR PARA PROJ/ATIV'
    em = EmuladorFalso(roteiro_linha_recusada_na_classificacao(mensagem))

    assert anulacao(em, data_row()) == (mensagem, '')


def test_rotulo_do_documento_sem_numero_nao_derruba_o_robo():
    """O [0] de um split() vazio estourava DEPOIS de o PF5 já ter sido
    enviado, deixando a linha sem resultado gravado."""
    roteiro = roteiro_linha_ok()
    roteiro[5] = {1: MSG_REGISTRO, 7: '   Nr. Documento Global:   '}
    em = EmuladorFalso(roteiro)

    assert aprovacao(em, data_row()) == (MSG_REGISTRO, '')


def test_pf5_que_nao_confirma_traz_o_motivo_da_janela_de_inconsistencia():
    roteiro = roteiro_linha_ok()
    roteiro[5] = {1: MSG_CONFIRMAR, 4: ' ' * 18 + MSG_INCONSISTENCIA}
    em = EmuladorFalso(roteiro)

    assert aprovacao(em, data_row()) == (MSG_INCONSISTENCIA, '')


def test_pf5_que_nao_confirma_sem_explicacao_devolve_a_propria_mensagem():
    roteiro = roteiro_linha_ok()
    roteiro[5] = {1: MSG_CONFIRMAR}
    em = EmuladorFalso(roteiro)

    assert aprovacao(em, data_row()) == (MSG_CONFIRMAR, '')
