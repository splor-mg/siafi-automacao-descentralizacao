"""Aviso de atualização na janela do robô.

Quem usa o robô são os órgãos: a janela do robo.bat é o único canal para
contar o que mudou. Se o aviso repetir toda vez ninguém lê; se sumir, a
mudança não chega.
"""
import pytest

import consolida
import novidades

TEXTO = """# instrução para quem escreve: não aparece

O ROBÔ FOI ATUALIZADO

- primeira mudança
"""


@pytest.fixture
def arquivos(tmp_path):
    arq = tmp_path / 'NOVIDADES.txt'
    arq.write_text(TEXTO, encoding='utf-8')
    return arq, tmp_path / 'data' / novidades.NOME_MARCADOR


def mostrar(arq, marcador, **kwargs):
    return novidades.mostrar(str(arq), str(marcador), **kwargs)


def test_mostra_uma_vez_so(arquivos, capsys):
    arq, marcador = arquivos

    assert mostrar(arq, marcador) is True
    saida = capsys.readouterr().out
    assert '  O ROBÔ FOI ATUALIZADO' in saida
    assert '  - primeira mudança' in saida
    assert 'instrução para quem escreve' not in saida

    assert mostrar(arq, marcador) is False
    assert capsys.readouterr().out == ''


def test_texto_novo_aparece_de_novo(arquivos):
    arq, marcador = arquivos
    mostrar(arq, marcador)

    arq.write_text(TEXTO + '- segunda mudança\n', encoding='utf-8')

    assert mostrar(arq, marcador) is True


def test_mexer_so_nos_comentarios_nao_repete_o_aviso(arquivos):
    arq, marcador = arquivos
    mostrar(arq, marcador)

    arq.write_text('# outra instrução\n' + TEXTO, encoding='utf-8')

    assert mostrar(arq, marcador) is False


@pytest.mark.parametrize('conteudo', [None, '', '# só comentário\n\n'])
def test_sem_texto_nao_mostra_nada(tmp_path, capsys, conteudo):
    arq = tmp_path / 'NOVIDADES.txt'
    if conteudo is not None:
        arq.write_text(conteudo, encoding='utf-8')
    marcador = tmp_path / 'data' / novidades.NOME_MARCADOR

    assert mostrar(arq, marcador) is False
    assert capsys.readouterr().out == ''
    assert not marcador.exists()


def test_registro_que_nao_pode_ser_gravado_so_avisa(arquivos, capsys):
    arq, marcador = arquivos
    marcador.parent.write_text('um arquivo no lugar da pasta')

    assert mostrar(arq, marcador) is True
    assert '[aviso]' in capsys.readouterr().out


def test_pausa_so_numa_janela_de_verdade(arquivos, monkeypatch):
    """Sem janela (o .exe antigo engole a saída), a pausa seria tempo perdido."""
    arq, marcador = arquivos
    pausas = []
    monkeypatch.setattr(novidades.time, 'sleep', pausas.append)

    mostrar(arq, marcador, terminal=False)
    marcador.unlink()
    mostrar(arq, marcador, terminal=True)

    assert pausas == [novidades.PAUSA_SEGUNDOS]


def test_consolida_mostra_o_aviso_antes_de_tudo(arquivos, monkeypatch, capsys):
    arq, marcador = arquivos
    monkeypatch.setattr(consolida, 'ARQUIVO_NOVIDADES', str(arq))
    monkeypatch.setattr(consolida, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.delenv('PASTA_WINDOWS', raising=False)

    assert consolida.main() == 1

    saida = capsys.readouterr().out
    assert saida.index('O ROBÔ FOI ATUALIZADO') < saida.index('PASTA_WINDOWS não configurada')
    assert marcador.exists()      # PASTA_LINUX aponta para tmp_path/data (conftest)


def test_falha_no_aviso_nao_impede_o_robo(monkeypatch, capsys):
    def com_defeito(*args, **kwargs):
        raise RuntimeError('defeito')

    monkeypatch.setattr(consolida.novidades, 'mostrar', com_defeito)
    monkeypatch.setattr(consolida, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.delenv('PASTA_WINDOWS', raising=False)

    assert consolida.main() == 1

    saida = capsys.readouterr().out
    assert '[aviso] não consegui mostrar o aviso de atualização' in saida
    assert 'PASTA_WINDOWS não configurada' in saida


def test_aviso_do_repositorio_cabe_na_janela():
    texto = novidades.ler_texto(consolida.ARQUIVO_NOVIDADES)

    assert texto.strip(), 'NOVIDADES.txt sem texto: nenhum aviso vai aparecer'
    assert all(len(linha) <= novidades.LARGURA - 2 for linha in texto.splitlines())
