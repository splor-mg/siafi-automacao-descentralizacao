"""Movimentação de arquivos: mexe em planilhas de produção no OneDrive.

Se o resgate falhar em silêncio, a pessoa corrige o problema, roda de novo e
recebe 'nenhuma planilha para processar' sem entender por quê.
"""
import pytest

import arquivos
from tests.conftest import envelhecer, escrever_planilha, linha


# --- trava --------------------------------------------------------------

def test_segunda_execucao_ao_mesmo_tempo_e_recusada():
    trava = arquivos.travar_execucao()

    with pytest.raises(arquivos.ExecucaoEmAndamento):
        arquivos.travar_execucao()

    trava.close()
    arquivos.travar_execucao().close()      # liberada: a seguinte entra


# --- mover --------------------------------------------------------------

def test_mover_para_pasta_nao_sobrescreve(tmp_path):
    destino = tmp_path / 'destino'
    destino.mkdir()
    (destino / 'a.xlsx').write_text('antigo')
    (tmp_path / 'a.xlsx').write_text('novo')

    final = arquivos.mover_para_pasta(str(tmp_path / 'a.xlsx'), str(destino))

    assert final == str(destino / 'a (1).xlsx')
    assert (destino / 'a.xlsx').read_text() == 'antigo'
    assert (destino / 'a (1).xlsx').read_text() == 'novo'


def test_mover_tenta_de_novo_quando_o_arquivo_esta_travado(tmp_path, monkeypatch):
    """Trava de sincronização do OneDrive dura alguns segundos e passa."""
    (tmp_path / 'a.xlsx').write_text('x')
    mover_de_verdade = arquivos.shutil.move
    tentativas = []

    def mover_travado_na_primeira(*args, **kwargs):
        tentativas.append(1)
        if len(tentativas) == 1:
            raise PermissionError('arquivo em uso')
        return mover_de_verdade(*args, **kwargs)

    monkeypatch.setattr(arquivos.shutil, 'move', mover_travado_na_primeira)

    arquivos.mover(str(tmp_path / 'a.xlsx'), str(tmp_path / 'b.xlsx'))

    assert len(tentativas) == 2
    assert (tmp_path / 'b.xlsx').read_text() == 'x'


def test_mover_desiste_e_avisa_quem_chamou(tmp_path, monkeypatch):
    (tmp_path / 'a.xlsx').write_text('x')

    def sempre_travado(*args, **kwargs):
        raise PermissionError('arquivo em uso')

    monkeypatch.setattr(arquivos.shutil, 'move', sempre_travado)

    with pytest.raises(PermissionError):
        arquivos.mover(str(tmp_path / 'a.xlsx'), str(tmp_path / 'b.xlsx'))
    assert (tmp_path / 'a.xlsx').exists()


def test_listar_ignora_o_arquivo_de_trava_do_excel(tmp_path):
    (tmp_path / 'planilha.xlsx').write_text('x')
    (tmp_path / '~$planilha.xlsx').write_text('x')
    (tmp_path / 'notas.txt').write_text('x')

    assert arquivos.listar_xlsx(str(tmp_path)) == [str(tmp_path / 'planilha.xlsx')]


# --- o que falta fazer numa conferência ----------------------------------

def test_conta_pendentes_e_preenchidas(tmp_path):
    arq = escrever_planilha(tmp_path / 'c.xlsx', [
        linha(Progresso='Ok - 123'),
        linha(Progresso='   '),          # só espaços não é 'preenchida'
        linha(),
    ])

    assert arquivos.contar_linhas(str(arq)) == (2, 1)


def test_arquivo_ilegivel_nao_tem_pendencia(tmp_path):
    (tmp_path / 'c.xlsx').write_text('isto não é um xlsx')

    assert arquivos.contar_linhas(str(tmp_path / 'c.xlsx')) == (0, 0)


def test_escolhe_a_conferencia_pendente_mais_recente(tmp_path):
    feita = escrever_planilha(tmp_path / 'feita.xlsx', [linha(Progresso='Ok')])
    antiga = escrever_planilha(tmp_path / 'antiga.xlsx', [linha()])
    nova = escrever_planilha(tmp_path / 'nova.xlsx', [linha()])
    envelhecer(antiga, 2)
    envelhecer(feita, 0)

    escolhida = arquivos.conferencia_a_processar(str(tmp_path))

    assert escolhida.caminho == str(nova)
    assert escolhida.pendentes == 1


def test_conferencia_parada_ha_muito_tempo_nao_e_retomada(tmp_path):
    """Arquivo esquecido de uma falha antiga, que a pessoa já resolveu à mão
    no SIAFI, não pode ser executado por um clique com a pasta vazia."""
    velha = escrever_planilha(tmp_path / 'velha.xlsx', [linha()])
    envelhecer(velha, 8)

    assert arquivos.conferencia_a_processar(str(tmp_path)) is None

    envelhecer(velha, 7)
    assert arquivos.conferencia_a_processar(str(tmp_path)) is not None


def test_limite_da_retomada_vem_do_env_na_hora_do_uso(tmp_path, monkeypatch):
    """O .env só é carregado depois de o módulo já ter sido importado."""
    velha = escrever_planilha(tmp_path / 'velha.xlsx', [linha()])
    envelhecer(velha, 20)

    monkeypatch.setenv('RETOMADA_MAX_DIAS', '30')
    assert arquivos.conferencia_a_processar(str(tmp_path)) is not None

    monkeypatch.setenv('RETOMADA_MAX_DIAS', 'trinta')      # valor inválido: padrão
    assert arquivos.conferencia_a_processar(str(tmp_path)) is None


def test_conferencia_toda_feita_nao_e_escolhida(tmp_path):
    escrever_planilha(tmp_path / 'feita.xlsx', [linha(Progresso='Ok')])

    assert arquivos.conferencia_a_processar(str(tmp_path)) is None


# --- manifesto: desfazer a consolidação -----------------------------------

def montar_consolidacao(tmp_path):
    """O estado deixado pelo consolida.py: entradas em Realizados, a
    conferência anterior arquivada, a nova na pasta e o manifesto de tudo."""
    entrada = tmp_path / 'Remanejados'
    realizados = tmp_path / 'Realizados'
    conferencia = tmp_path / 'Conferencia'
    arquivadas = tmp_path / 'Conferencia Realizados'
    for pasta in (entrada, realizados, conferencia, arquivadas):
        pasta.mkdir()
    manifesto = tmp_path / 'data' / '.movidos'

    arquivos.iniciar_manifesto(str(manifesto))
    (arquivadas / 'Conferencia 10.11.xlsx').write_text('anterior')
    arquivos.registrar_movido(str(manifesto),
                              str(arquivadas / 'Conferencia 10.11.xlsx'),
                              str(conferencia / 'Conferencia 10.11.xlsx'))
    (conferencia / 'Conferencia 11.11.xlsx').write_text('nova')
    arquivos.registrar_conferencia(str(manifesto),
                                   str(conferencia / 'Conferencia 11.11.xlsx'))
    for nome in ('a.xlsx', 'b.xlsx'):
        (realizados / nome).write_text(nome)
        arquivos.registrar_movido(str(manifesto), str(realizados / nome),
                                  str(entrada / nome))
    return entrada, realizados, conferencia, arquivadas, manifesto


def test_desfazer_devolve_tudo_para_o_lugar(tmp_path):
    entrada, realizados, conferencia, arquivadas, manifesto = montar_consolidacao(tmp_path)

    devolvidos, nao_devolvidos = arquivos.desfazer_consolidacao(str(manifesto))

    assert sorted(p.name for p in entrada.iterdir()) == ['a.xlsx', 'b.xlsx']
    assert list(realizados.iterdir()) == []
    # a conferência nova some e a anterior volta a ser a da pasta
    assert [p.name for p in conferencia.iterdir()] == ['Conferencia 10.11.xlsx']
    assert list(arquivadas.iterdir()) == []
    assert len(devolvidos) == 3 and nao_devolvidos == []
    assert not manifesto.exists()


def test_desfazer_apaga_a_conferencia_onde_ela_estiver(tmp_path):
    """O robô já a trouxe para a pasta local quando decide desfazer."""
    _e, _r, conferencia, _a, manifesto = montar_consolidacao(tmp_path)
    local = tmp_path / 'data' / 'Conferencia 11.11.xlsx'
    (conferencia / 'Conferencia 11.11.xlsx').rename(local)

    arquivos.desfazer_consolidacao(str(manifesto), str(local))

    assert not local.exists()


def test_desfazer_nao_sobrescreve_planilha_que_ja_esta_na_fila(tmp_path):
    """A pessoa pode ter posto a versão corrigida com o mesmo nome."""
    entrada, realizados, _c, _a, manifesto = montar_consolidacao(tmp_path)
    (entrada / 'a.xlsx').write_text('versão corrigida')

    devolvidos, nao_devolvidos = arquivos.desfazer_consolidacao(str(manifesto))

    assert (entrada / 'a.xlsx').read_text() == 'versão corrigida'
    assert (realizados / 'a.xlsx').exists()
    assert nao_devolvidos == ['a.xlsx']
    assert str(entrada / 'b.xlsx') in devolvidos


def test_desfazer_sem_manifesto_nao_faz_nada_nem_quebra(tmp_path):
    assert arquivos.desfazer_consolidacao(str(tmp_path / 'nao-existe')) == ([], [])


def test_desfazer_ignora_arquivo_que_ja_nao_esta_la(tmp_path):
    """Alguém pode ter mexido em Realizados à mão entre uma coisa e outra."""
    entrada, realizados, _c, _a, manifesto = montar_consolidacao(tmp_path)
    (realizados / 'a.xlsx').unlink()

    devolvidos, nao_devolvidos = arquivos.desfazer_consolidacao(str(manifesto))

    assert [p.name for p in entrada.iterdir()] == ['b.xlsx']
    assert nao_devolvidos == []


def test_manifesto_novo_apaga_o_da_execucao_anterior(tmp_path):
    _e, _r, _c, _a, manifesto = montar_consolidacao(tmp_path)

    arquivos.iniciar_manifesto(str(manifesto))

    assert arquivos.ler_manifesto(str(manifesto)) == (None, [])


# --- conferência que ficou na pasta local ---------------------------------

def test_recupera_a_conferencia_deixada_na_pasta_local(tmp_path):
    em_processamento = tmp_path / 'data' / 'em_processamento'
    conferencia = tmp_path / 'Conferencia'
    em_processamento.mkdir(parents=True)
    conferencia.mkdir()
    (em_processamento / 'Conferencia 11.11.xlsx').write_text('parcial')

    devolvidas = arquivos.recuperar_interrompidas(str(em_processamento),
                                                  str(conferencia))

    assert devolvidas == [str(conferencia / 'Conferencia 11.11.xlsx')]
    assert list(em_processamento.iterdir()) == []


def test_recuperar_sem_pasta_local_nao_quebra(tmp_path):
    assert arquivos.recuperar_interrompidas(str(tmp_path / 'nao-existe'),
                                            str(tmp_path)) == []
