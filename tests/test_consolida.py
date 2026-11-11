"""Consolidação das planilhas de entrada.

O que mais importa aqui é o que acontece quando NÃO dá certo: nada pode ficar
pela metade, com planilha em "Realizados" que nunca foi executada.
"""
import pandas as pd
import pytest

import arquivos
import consolida
from tests.conftest import envelhecer, escrever_planilha, linha


def rodar(projeto):
    return consolida.consolidar(str(projeto.windows), str(projeto.local))


def ler(caminho):
    return pd.read_excel(caminho, sheet_name=arquivos.ABA)


def conferencia_gerada(projeto):
    (nome,) = projeto.nomes(projeto.conferencia)
    return projeto.conferencia / nome


# --- caminho feliz ---------------------------------------------------------

def test_consolida_ordena_anulacoes_primeiro_e_tira_as_entradas_da_fila(projeto):
    escrever_planilha(projeto.remanejados / 'a.xlsx', [
        linha('Aprovar', valor=100), linha('Anular', valor=200)])
    escrever_planilha(projeto.remanejados / 'b.xlsx', [linha('anular', valor=300)])

    assert rodar(projeto) == 0

    df = ler(conferencia_gerada(projeto))
    assert list(df['Orientacao']) == ['Anular', 'Anular', 'Aprovar']
    assert list(df['Valor']) == [200, 300, 100]
    assert projeto.nomes(projeto.remanejados) == []
    assert projeto.nomes(projeto.realizados_rem) == ['a.xlsx', 'b.xlsx']


def test_campos_saem_normalizados_na_conferencia(projeto):
    """Número guardado como texto passava na validação e derrubava o robô lá
    na frente, com o SIAFI já aberto."""
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha(
        orientacao=' APROVAR ', tipo='global', valor='1.500,50',
        **{'UE_Beneficiada': '1500008', 'Elemento 92': 'n', 'Acao': '2500,0'})])

    assert rodar(projeto) == 0

    (registro,) = ler(conferencia_gerada(projeto)).to_dict('records')
    assert registro['Orientacao'] == 'Aprovar'
    assert registro['Tipo de Descentralizacao'] == 'Global'
    assert registro['Elemento 92'] == 'N'
    assert registro['UE_Beneficiada'] == 1500008
    assert registro['Acao'] == 2500
    assert registro['Valor'] == 1500.50


def test_linha_so_com_anotacao_solta_nao_vira_operacao(projeto):
    planilha = escrever_planilha(projeto.remanejados / 'a.xlsx', [linha()])
    df = ler(planilha)
    df['Progresso'] = df['Progresso'].astype('object')
    df.loc[5, 'Progresso'] = 'lembrar de conferir'   # linha sem nenhum dado
    df.to_excel(planilha, sheet_name=arquivos.ABA, index=False)

    assert rodar(projeto) == 0
    assert len(ler(conferencia_gerada(projeto))) == 1


def test_conferencia_anterior_concluida_e_arquivada(projeto):
    escrever_planilha(projeto.conferencia / 'Conferencia Arquivo Robo 10.11.xlsx',
                      [linha(Progresso='Ok - 1')])
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha()])

    assert rodar(projeto) == 0

    assert projeto.nomes(projeto.realizados_conf) == ['Conferencia Arquivo Robo 10.11.xlsx']
    assert len(projeto.nomes(projeto.conferencia)) == 1


def test_avisa_quando_arquiva_conferencia_com_linha_nao_executada(projeto, capsys):
    """Chegou planilha nova: a antiga não é retomada, mas o que ficou sem
    fazer nela não pode sumir em silêncio."""
    escrever_planilha(projeto.conferencia / 'Conferencia Arquivo Robo 10.11.xlsx',
                      [linha(Progresso='Ok - 1'), linha(), linha()])
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha()])

    assert rodar(projeto) == 0

    saida = capsys.readouterr().out
    assert '[ATENÇÃO]' in saida and '2 linha(s) sem Progresso' in saida


# --- validação ---------------------------------------------------------------

def test_erro_de_preenchimento_aborta_sem_mover_nada(projeto, capsys):
    escrever_planilha(projeto.remanejados / 'boa.xlsx', [linha()])
    escrever_planilha(projeto.remanejados / 'ruim.xlsx', [linha(), linha(IAG=7)])
    escrever_planilha(projeto.conferencia / 'anterior.xlsx', [linha(Progresso='Ok')])

    assert rodar(projeto) == 1

    assert projeto.nomes(projeto.remanejados) == ['boa.xlsx', 'ruim.xlsx']
    assert projeto.nomes(projeto.conferencia) == ['anterior.xlsx']
    assert projeto.nomes(projeto.realizados_rem) == []
    assert "ruim.xlsx | linha 3 | coluna 'IAG'" in capsys.readouterr().out


def test_planilha_sem_a_aba_ou_sem_colunas_e_erro_claro(projeto, capsys):
    escrever_planilha(projeto.remanejados / 'outra_aba.xlsx', [linha()], aba='Planilha1')
    pd.DataFrame({'Orientacao': ['Aprovar']}).to_excel(
        projeto.remanejados / 'sem_colunas.xlsx', sheet_name=arquivos.ABA, index=False)

    assert rodar(projeto) == 1

    saida = capsys.readouterr().out
    assert "outra_aba.xlsx | arquivo | não tem a aba 'Execucao'" in saida
    assert 'sem_colunas.xlsx | estrutura | colunas obrigatórias ausentes' in saida


def test_xls_antigo_e_erro_com_instrucao_e_nao_some_calado(projeto, capsys):
    """Sem o xlrd o .xls nem abre: antes saía 'Missing optional dependency'."""
    (projeto.remanejados / 'antiga.xls').write_bytes(b'qualquer coisa')

    assert rodar(projeto) == 1
    assert 'antiga.xls' in capsys.readouterr().out
    assert projeto.nomes(projeto.remanejados) == ['antiga.xls']


def test_arquivo_de_trava_do_excel_e_ignorado(projeto):
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha()])
    (projeto.remanejados / '~$a.xlsx').write_bytes(b'trava')

    assert rodar(projeto) == 0


# --- pasta de entrada vazia ----------------------------------------------------

def test_sem_planilha_e_sem_pendencia_nao_ha_o_que_fazer(projeto):
    escrever_planilha(projeto.conferencia / 'feita.xlsx', [linha(Progresso='Ok')])

    assert rodar(projeto) == 2
    assert projeto.nomes(projeto.conferencia) == ['feita.xlsx']


def test_sem_planilha_nova_retoma_a_conferencia_interrompida(projeto, capsys):
    """Sem isto a execução seguinte dizia 'nada a consolidar' e as linhas por
    fazer ficavam presas até alguém refazer a planilha à mão."""
    projeto.interrompida(escrever_planilha(projeto.conferencia / 'interrompida.xlsx', [
        linha(Progresso='Ok - 1'), linha(Progresso='INTERROMPIDA - VERIFICAR NO SIAFI'),
        linha()]))

    assert rodar(projeto) == 0

    assert projeto.nomes(projeto.conferencia) == ['interrompida.xlsx']
    assert '1 linha(s) ainda por fazer' in capsys.readouterr().out


def test_conferencia_antiga_nao_e_retomada_e_o_motivo_e_dito(projeto, capsys):
    antiga = projeto.interrompida(
        escrever_planilha(projeto.conferencia / 'antiga.xlsx', [linha()]))
    envelhecer(antiga, 30)

    assert rodar(projeto) == 2
    assert 'NÃO é retomada' in capsys.readouterr().out


def test_conferencia_pendente_deixada_pela_versao_antiga_nao_e_executada(projeto, capsys):
    """A versão anterior não marcava a linha em curso: uma linha em branco
    pode já estar no SIAFI, ou ter sido lançada à mão pelo órgão depois de uma
    falha. Retomar sozinho duplicaria a operação."""
    deixada = escrever_planilha(projeto.conferencia / 'Conferencia Arquivo Robo 10.11.xlsx',
                                [linha(Progresso='Ok - 1'), linha()])

    assert rodar(projeto) == 2

    assert projeto.progresso(deixada) == ['Ok - 1', '']
    assert 'NÃO é executada sozinha' in capsys.readouterr().out


# --- falha no meio da consolidação ---------------------------------------------

def test_falha_ao_mover_uma_entrada_desfaz_tudo(projeto, monkeypatch):
    """Planilha aberta no Excel não sai da pasta. Antes a consolidação parava
    ali, com parte das entradas já em Realizados: na execução seguinte só a
    que sobrou era processada, e as outras nunca chegavam ao SIAFI."""
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha()])
    escrever_planilha(projeto.remanejados / 'b.xlsx', [linha()])
    escrever_planilha(projeto.conferencia / 'anterior.xlsx', [linha(Progresso='Ok')])
    mover_de_verdade = arquivos.mover_para_pasta

    def b_aberta_no_excel(origem, pasta_destino, **kwargs):
        if origem.endswith('b.xlsx'):
            raise PermissionError('b.xlsx está em uso')
        return mover_de_verdade(origem, pasta_destino, **kwargs)

    monkeypatch.setattr(arquivos, 'mover_para_pasta', b_aberta_no_excel)

    assert rodar(projeto) == 1

    assert projeto.nomes(projeto.remanejados) == ['a.xlsx', 'b.xlsx']
    assert projeto.nomes(projeto.realizados_rem) == []
    assert projeto.nomes(projeto.conferencia) == ['anterior.xlsx']
    assert projeto.nomes(projeto.realizados_conf) == []
    assert not projeto.manifesto.exists()


def test_consolidacao_que_nao_chegou_ao_siafi_e_refeita_com_as_planilhas_novas(projeto):
    """A janela foi fechada entre a consolidação e o robô. As planilhas da
    primeira rodada voltam para a fila e entram junto com a que chegou depois."""
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha(), linha()])
    assert rodar(projeto) == 0
    escrever_planilha(projeto.remanejados / 'b.xlsx', [linha()])

    assert rodar(projeto) == 0

    assert len(ler(conferencia_gerada(projeto))) == 3
    assert projeto.nomes(projeto.realizados_rem) == ['a.xlsx', 'b.xlsx']
    assert projeto.nomes(projeto.realizados_conf) == []


def test_conferencia_deixada_na_pasta_local_volta_e_e_retomada(projeto):
    """Janela fechada no meio do envio: o arquivo ficava dentro do WSL."""
    projeto.em_processamento.mkdir()
    escrever_planilha(projeto.em_processamento / 'Conferencia Arquivo Robo 11.11.xlsx', [
        linha(Progresso='Ok - 1'),
        linha(Progresso='INTERROMPIDA - VERIFICAR NO SIAFI'), linha()])

    assert rodar(projeto) == 0

    assert projeto.nomes(projeto.conferencia) == ['Conferencia Arquivo Robo 11.11.xlsx']
    assert projeto.nomes(projeto.em_processamento) == []
    assert projeto.retomaveis() == {str(projeto.conferencia / 'Conferencia Arquivo Robo 11.11.xlsx')}


def test_arquivo_solto_de_versao_antiga_na_pasta_local_nao_e_tocado(projeto):
    """Não dá para saber de quando é nem o que já foi feito à mão no SIAFI."""
    escrever_planilha(projeto.local / 'Conferencia Arquivo Robo 02.07.xlsx',
                      [linha(Progresso='Ok'), linha()])

    assert rodar(projeto) == 2

    assert projeto.nomes(projeto.local) == ['Conferencia Arquivo Robo 02.07.xlsx']
    assert projeto.nomes(projeto.conferencia) == []


# --- trava -----------------------------------------------------------------------

def test_nao_roda_com_outra_execucao_em_andamento(projeto):
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha()])
    trava = arquivos.travar_execucao()

    assert rodar(projeto) == 10

    assert projeto.nomes(projeto.remanejados) == ['a.xlsx']
    trava.close()


def test_main_sem_pasta_configurada_explica_e_sai(monkeypatch, capsys):
    monkeypatch.setattr(consolida, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.delenv('PASTA_WINDOWS', raising=False)

    assert consolida.main() == 1
    assert 'PASTA_WINDOWS não configurada' in capsys.readouterr().out


@pytest.mark.parametrize('nome', ['apoio.xlsm', 'dados.csv'])
def test_planilha_em_outro_formato_e_avisada_mas_nao_impede(projeto, capsys, nome):
    escrever_planilha(projeto.remanejados / 'a.xlsx', [linha()])
    (projeto.remanejados / nome).write_bytes(b'x')

    assert rodar(projeto) == 0
    assert f"'{nome}' não é .xlsx" in capsys.readouterr().out
