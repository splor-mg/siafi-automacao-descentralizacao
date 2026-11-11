"""Regras de preenchimento de uma linha.

É a última barreira antes do SIAFI: o que passa aqui é digitado no terminal.
"""
import pytest

from tests.conftest import linha
from validacao import descrever_erros, inteiro, numero, validar_linha


def validar(**colunas):
    dados = linha(**colunas)
    return validar_linha(dados.get)


def colunas_com_erro(erros):
    return [coluna for coluna, _mensagem, _valor in erros]


def test_linha_valida_sai_na_forma_canonica():
    valores, erros = validar(orientacao=' aprovar ', tipo='GLOBAL',
                             **{'Elemento 92': 'n', 'UE_Beneficiada': 1500008.0})

    assert erros == []
    assert valores['Orientacao'] == 'Aprovar'
    assert valores['Tipo de Descentralizacao'] == 'Global'
    assert valores['Elemento 92'] == 'N'
    assert valores['UE_Beneficiada'] == 1500008
    assert valores['Valor'] == 1500.50


def test_lista_todos_os_erros_de_uma_vez():
    """A pessoa precisa ver tudo o que corrigir, não um erro por rodada."""
    _valores, erros = validar(orientacao='Remanejar', Acao=25, IAG=3)

    assert colunas_com_erro(erros) == ['Orientacao', 'Acao', 'IAG']


@pytest.mark.parametrize('coluna, valor', [
    ('UE_Beneficiada', 150008),         # 6 dígitos
    ('UE_Beneficiada', 'abc'),
    ('Fonte', 0),
    ('Fonte', 100),
    ('Procedencia', 10),
    ('Elemento 92', 'X'),
    ('Elemento 92', None),
    ('Acao', 25000),
    ('Natureza_Despesa_Elemento', 33903),
    ('IAG', 2),
    ('IAG', None),
])
def test_valor_fora_da_regra_reprova_a_coluna(coluna, valor):
    _valores, erros = validar(**{coluna: valor})

    assert colunas_com_erro(erros) == [coluna]


def test_item_so_e_exigido_no_amarrado():
    assert validar(tipo='Global', Item=None)[1] == []
    assert colunas_com_erro(validar(tipo='Amarrado', Item=None)[1]) == ['Item']
    assert validar(tipo='Amarrado', Item=7)[0]['Item'] == 7


def test_uo_financiadora_so_e_exigida_na_procedencia_2():
    assert validar(Procedencia=1, UO_Financiadora=None)[1] == []
    _valores, erros = validar(Procedencia=2, UO_Financiadora=None)
    assert colunas_com_erro(erros) == ['UO_Financiadora']
    assert validar(Procedencia=2, UO_Financiadora=2271)[0]['UO_Financiadora'] == 2271


def test_campo_que_a_linha_nao_usa_nao_derruba_a_validacao():
    """Um traço no Item de uma linha Global derrubava o robô com o SIAFI já
    aberto: a validação não olhava a célula, mas a conversão sim."""
    valores, erros = validar(tipo='Global', Item='-', Procedencia=1,
                             UO_Financiadora='n/a')

    assert erros == []
    assert 'Item' not in valores
    assert 'UO_Financiadora' not in valores


@pytest.mark.parametrize('valor', [0, -100, '0', None, '', 'mil reais'])
def test_valor_precisa_ser_numero_maior_que_zero(valor):
    """O sentido da operação vem da Orientacao, nunca do sinal do valor."""
    _valores, erros = validar(valor=valor)

    assert colunas_com_erro(erros) == ['Valor']


@pytest.mark.parametrize('texto, esperado', [
    ('1500', 1500.0),
    ('1500,5', 1500.5),
    ('1500.50', 1500.5),
    ('1.500,50', 1500.5),
    ('12.345.678,9', 12345678.9),
    (' 250,00 ', 250.0),
])
def test_valor_em_texto_sem_ambiguidade_e_aceito(texto, esperado):
    assert numero(texto) == esperado


@pytest.mark.parametrize('texto', ['1.500', '1,500', '1.500.000', '1,500.00',
                                   'R$ 1500', '1e3', '15,555'])
def test_valor_em_texto_ambiguo_e_recusado(texto):
    """'1.500' em português é mil e quinhentos; o float() do Python lê um e
    meio, e o robô enviaria R$ 1,50 ao SIAFI. Na dúvida, não envia."""
    assert numero(texto) is None


def test_valor_numerico_do_excel_passa_como_esta():
    assert numero(1500.5) == 1500.5
    assert numero(1500) == 1500.0
    assert numero(float('nan')) is None
    assert numero(True) is None


def test_inteiro_aceita_numero_guardado_como_texto_ou_decimal():
    assert inteiro(1500008.0) == 1500008
    assert inteiro(' 2500 ') == 2500
    assert inteiro('2500,0') == 2500
    assert inteiro(2500.5) is None
    assert inteiro('abc') is None
    assert inteiro(None) is None
    assert inteiro(True) is None


def test_descricao_dos_erros_mostra_o_que_foi_encontrado():
    _valores, erros = validar(IAG=3)

    assert descrever_erros(erros) == 'IAG deve ser 0 ou 1 (encontrado: 3)'
