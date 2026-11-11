"""O robô de ponta a ponta, com um SIAFI de mentira.

Cobre o que quem usa o robô num órgão precisa que seja verdade: se parar antes
de enviar, as planilhas voltam para a fila; se parar no meio, a conferência
volta com o que foi feito, nenhuma linha é enviada duas vezes e a execução
seguinte continua de onde parou.
"""
import pytest
from py3270 import CommandError

import arquivos
import consolida
import descentralizacao
from descentralizacao import (PROGRESSO_INCERTO, PROGRESSO_SEM_RETORNO,
                              executar, traduzir_progresso)
from tests.conftest import escrever_planilha, linha
from tests.emulador_falso import (MSG_REGISTRO, VAZIA, EmuladorFalso, Fabrica,
                                  roteiro_linha_ok,
                                  roteiro_linha_recusada_na_classificacao,
                                  roteiro_login)


def consolidar(projeto):
    return consolida.consolidar(str(projeto.windows), str(projeto.local))


def conferencia_gerada(projeto):
    (nome,) = projeto.nomes(projeto.conferencia)
    return projeto.conferencia / nome


def entrada_com(projeto, *linhas, nome='pedido.xlsx'):
    escrever_planilha(projeto.remanejados / nome, list(linhas))
    assert consolidar(projeto) == 0


# --- caminho feliz ---------------------------------------------------------------

def test_processa_todas_as_linhas_e_devolve_a_conferencia(projeto):
    entrada_com(projeto, linha('Aprovar', 'Amarrado'), linha('Anular'))
    em = EmuladorFalso(roteiro_login()
                       + roteiro_linha_ok('2026000001')
                       + roteiro_linha_ok('2026000002'))

    assert executar(projeto.cfg, Fabrica(em)) == 0

    assert projeto.progresso(conferencia_gerada(projeto)) == [
        'Ok - 2026000001', 'Ok - 2026000002']
    assert projeto.nomes(projeto.em_processamento) == []
    assert projeto.nomes(projeto.realizados_rem) == ['pedido.xlsx']
    assert not projeto.manifesto.exists()
    assert em.terminado and em.roteiro == []
    # anulação primeiro (opção 02), depois a aprovação (opção 01)
    opcoes = [c[3] for c in em.digitado() if c[:3] == ('fill_field', 21, 19)]
    assert opcoes == ['03', '03', '02', '01']


def test_login_digita_as_credenciais_do_env_e_respeita_o_modo_de_tela(projeto):
    entrada_com(projeto, linha())
    em = EmuladorFalso(roteiro_login() + roteiro_linha_ok())
    cfg = dict(projeto.cfg, visivel=True)

    assert executar(cfg, Fabrica(em)) == 0

    assert em.visible is True
    assert em.chamadas[0] == ('connect', 'siafi.teste')
    assert em.digitado()[:4] == [
        ('fill_field', 19, 13, 'simg', 8),
        ('fill_field', 20, 13, 'M1234567', 8),
        ('fill_field', 21, 13, 'segredo1', 8),      # senha de 8 caracteres cabe
        ('send_enter',),
    ]
    assert ('fill_field', 22, 30, '1500008', 7) in em.digitado()


def test_recusa_do_siafi_vai_para_o_progresso_e_o_robo_segue(projeto):
    entrada_com(projeto, linha(valor=100), linha(valor=200))
    em = EmuladorFalso(
        roteiro_login()
        + roteiro_linha_recusada_na_classificacao('E90 - SALDO ZERADO NA CONTA 123')
        + roteiro_linha_ok('2026000009'))

    assert executar(projeto.cfg, Fabrica(em)) == 0

    assert projeto.progresso(conferencia_gerada(projeto)) == [
        'Saldo zerado na conta', 'Ok - 2026000009']


# --- parou ANTES de enviar: as planilhas voltam para a fila ------------------------

def test_sem_conexao_desfaz_a_consolidacao(projeto, capsys):
    """VPN desligada. Sem devolver, a pessoa liga a VPN, roda de novo e
    recebe 'nenhuma planilha para processar'."""
    escrever_planilha(projeto.conferencia / 'anterior.xlsx', [linha(Progresso='Ok')])
    entrada_com(projeto, linha())
    sem_rede = [EmuladorFalso(falha_ao_conectar=CommandError('Connection timed out'))
                for _ in range(2)]

    assert executar(projeto.cfg, Fabrica(*sem_rede)) == 1

    assert projeto.nomes(projeto.remanejados) == ['pedido.xlsx']
    assert projeto.nomes(projeto.realizados_rem) == []
    assert projeto.nomes(projeto.conferencia) == ['anterior.xlsx']
    assert projeto.nomes(projeto.em_processamento) == []
    assert not projeto.manifesto.exists()
    assert all(em.terminado for em in sem_rede)
    saida = capsys.readouterr().out
    assert 'Não foi possível conectar ao SIAFI após 2 tentativa(s)' in saida
    assert 'NADA foi enviado ao SIAFI' in saida


def test_conexao_que_falha_na_primeira_tentativa_e_refeita(projeto):
    entrada_com(projeto, linha())
    falhou = EmuladorFalso(falha_ao_conectar=CommandError('Connection timed out'))
    conectou = EmuladorFalso(roteiro_login() + roteiro_linha_ok())

    assert executar(projeto.cfg, Fabrica(falhou, conectou)) == 0
    assert falhou.terminado


def test_sessao_recusada_pelo_mainframe_conta_como_falha_de_conexao(projeto):
    entrada_com(projeto, linha())
    recusado = EmuladorFalso()
    recusado.tela = {1: ' UNABLE TO ESTABLISH SESSION'}
    conectou = EmuladorFalso(roteiro_login() + roteiro_linha_ok())

    assert executar(projeto.cfg, Fabrica(recusado, conectou)) == 0


@pytest.mark.parametrize('telas_ate_o_aviso', [
    [{23: 'SENHA EXPIRADA - INFORME NOVA SENHA'}],               # logo após o Enter
    [VAZIA, VAZIA, {5: '   Senha expirada. Troque a senha.'}],   # numa tela adiante, outra linha
])
def test_senha_expirada_sai_com_codigo_3_e_devolve_as_planilhas(projeto, telas_ate_o_aviso):
    entrada_com(projeto, linha())
    em = EmuladorFalso(telas_ate_o_aviso)

    assert executar(projeto.cfg, Fabrica(em)) == 3

    assert projeto.nomes(projeto.remanejados) == ['pedido.xlsx']
    assert projeto.nomes(projeto.conferencia) == []
    assert em.terminado


def test_login_que_nunca_chega_ao_sucesso_para_sem_enviar_nada(projeto):
    entrada_com(projeto, linha())
    em = EmuladorFalso([VAZIA] * 30)

    assert executar(projeto.cfg, Fabrica(em)) == 1

    assert projeto.nomes(projeto.remanejados) == ['pedido.xlsx']
    assert em.terminado


def test_env_incompleto_para_antes_de_abrir_o_siafi(projeto, capsys):
    """Senha maior que o campo fazia o py3270 estourar com a própria senha na
    mensagem de erro, na tela de quem está usando."""
    entrada_com(projeto, linha())
    cfg = dict(projeto.cfg, senha='senha-comprida-demais', unidade_orcamentaria='')
    fabrica = Fabrica()

    assert executar(cfg, fabrica) == 1

    assert fabrica.criados == []
    assert projeto.nomes(projeto.remanejados) == ['pedido.xlsx']
    saida = capsys.readouterr().out
    assert 'SENHA tem mais de 8 caracteres' in saida
    assert 'UNIDADE_ORCAMENTARIA não está preenchido' in saida
    assert 'senha-comprida-demais' not in saida


def test_conferencia_aberta_no_excel_nao_deixa_duas_copias(projeto, monkeypatch, capsys):
    """Com a planilha aberta, a cópia vai e o original não sai. Duas cópias da
    mesma conferência fariam as mesmas linhas serem enviadas duas vezes."""
    projeto.interrompida(escrever_planilha(projeto.conferencia / 'interrompida.xlsx',
                                           [linha(Progresso='Ok - 1'), linha()]))

    def copia_e_nao_apaga(origem, destino, **kwargs):
        arquivos.shutil.copyfile(origem, destino)
        raise PermissionError('arquivo em uso')

    monkeypatch.setattr(arquivos.shutil, 'move', copia_e_nao_apaga)
    fabrica = Fabrica()

    assert executar(projeto.cfg, fabrica) == 1

    assert projeto.nomes(projeto.conferencia) == ['interrompida.xlsx']
    assert projeto.nomes(projeto.em_processamento) == []
    assert fabrica.criados == []
    assert 'feche-a' in capsys.readouterr().out


# --- parou NO MEIO: a conferência volta e a execução seguinte continua -------------

def cenario_interrompido(projeto):
    """Três linhas; o SIAFI trava o teclado no meio da segunda."""
    entrada_com(projeto, linha(valor=100), linha(valor=200), linha(valor=300))
    em = EmuladorFalso(roteiro_login() + roteiro_linha_ok('2026000001')
                       + [VAZIA, VAZIA, CommandError('Keyboard locked')])
    return em


def test_erro_no_meio_devolve_a_conferencia_com_o_que_foi_feito(projeto, capsys):
    em = cenario_interrompido(projeto)

    with pytest.raises(CommandError):
        executar(projeto.cfg, Fabrica(em))

    assert projeto.retomaveis() == {str(conferencia_gerada(projeto))}

    assert projeto.progresso(conferencia_gerada(projeto)) == [
        'Ok - 2026000001', PROGRESSO_INCERTO, '']
    assert projeto.nomes(projeto.em_processamento) == []
    # as entradas NÃO voltam: parte delas já está no SIAFI
    assert projeto.nomes(projeto.remanejados) == []
    assert projeto.nomes(projeto.realizados_rem) == ['pedido.xlsx']
    assert em.terminado
    saida = capsys.readouterr().out
    assert 'a linha 3 da conferência parou no meio' in saida
    assert 'TELA DO SIAFI' in saida


def test_execucao_seguinte_continua_de_onde_parou_sem_repetir_linha(projeto):
    with pytest.raises(CommandError):
        executar(projeto.cfg, Fabrica(cenario_interrompido(projeto)))

    assert consolidar(projeto) == 0             # pasta vazia: retoma
    em = EmuladorFalso(roteiro_login() + roteiro_linha_ok('2026000003'))
    assert executar(projeto.cfg, Fabrica(em)) == 0

    assert projeto.progresso(conferencia_gerada(projeto)) == [
        'Ok - 2026000001', PROGRESSO_INCERTO, 'Ok - 2026000003']
    valores = [c[3] for c in em.digitado() if c[:3] == ('fill_field', 17, 63)]
    assert valores == ['30000']                 # só a linha que faltava
    assert projeto.retomaveis() == set()        # foi até o fim: nada a retomar


def test_linha_em_curso_fica_marcada_no_arquivo_antes_de_ir_ao_siafi(projeto):
    """Se a janela do robô for fechada no meio, nenhum 'except' roda. A marca
    precisa já estar gravada, senão a linha seria reenviada às cegas."""
    entrada_com(projeto, linha())
    visto = {}

    class EspiaOArquivo(EmuladorFalso):
        def send_pf(self, numero):
            if numero == 5 and 'progresso' not in visto:
                (nome,) = projeto.nomes(projeto.em_processamento)
                visto['progresso'] = projeto.progresso(projeto.em_processamento / nome)
            super().send_pf(numero)

    em = EspiaOArquivo(roteiro_login() + roteiro_linha_ok())

    assert executar(projeto.cfg, Fabrica(em)) == 0
    assert visto['progresso'] == [PROGRESSO_INCERTO]


def test_janela_fechada_no_meio_e_recuperada_na_execucao_seguinte(projeto):
    """O estado que um processo morto deixa: a conferência na pasta local,
    com a linha em curso marcada."""
    projeto.em_processamento.mkdir()
    escrever_planilha(projeto.em_processamento / 'Conferencia Arquivo Robo 11.11.xlsx', [
        linha(valor=100, Progresso='Ok - 1'),
        linha(valor=200, Progresso=PROGRESSO_INCERTO),
        linha(valor=300)])
    em = EmuladorFalso(roteiro_login() + roteiro_linha_ok('2026000003'))

    assert executar(projeto.cfg, Fabrica(em)) == 0

    assert projeto.progresso(conferencia_gerada(projeto)) == [
        'Ok - 1', PROGRESSO_INCERTO, 'Ok - 2026000003']


def test_falha_antes_de_enviar_numa_retomada_devolve_a_conferencia_intacta(projeto):
    projeto.interrompida(escrever_planilha(projeto.conferencia / 'interrompida.xlsx',
                                           [linha(Progresso='Ok - 1'), linha()]))
    sem_rede = [EmuladorFalso(falha_ao_conectar=CommandError('timeout'))
                for _ in range(2)]

    assert executar(projeto.cfg, Fabrica(*sem_rede)) == 1

    assert projeto.progresso(projeto.conferencia / 'interrompida.xlsx') == ['Ok - 1', '']
    assert projeto.nomes(projeto.em_processamento) == []


def test_ctrl_c_no_meio_tambem_devolve_a_conferencia(projeto):
    entrada_com(projeto, linha(valor=100), linha(valor=200))
    em = EmuladorFalso(roteiro_login() + roteiro_linha_ok('2026000001')
                       + [VAZIA, KeyboardInterrupt()])

    assert executar(projeto.cfg, Fabrica(em)) == 130

    assert projeto.progresso(conferencia_gerada(projeto)) == [
        'Ok - 2026000001', PROGRESSO_INCERTO]
    assert em.terminado


def test_falha_ao_devolver_deixa_a_planilha_para_a_proxima_execucao(projeto, monkeypatch):
    """OneDrive travado na hora de devolver: a planilha fica na pasta local e
    a execução seguinte a leva de volta sozinha."""
    em = cenario_interrompido(projeto)
    mover_de_verdade = arquivos.mover

    def onedrive_travado(origem, destino, **kwargs):
        if destino.startswith(str(projeto.conferencia)):
            raise PermissionError('destino travado')
        return mover_de_verdade(origem, destino, **kwargs)

    monkeypatch.setattr(arquivos, 'mover', onedrive_travado)
    with pytest.raises(CommandError):
        executar(projeto.cfg, Fabrica(em))
    assert len(projeto.nomes(projeto.em_processamento)) == 1
    monkeypatch.setattr(arquivos, 'mover', mover_de_verdade)

    assert consolidar(projeto) == 0

    assert projeto.nomes(projeto.em_processamento) == []
    assert projeto.progresso(conferencia_gerada(projeto)) == [
        'Ok - 2026000001', PROGRESSO_INCERTO, '']


# --- conferência editada à mão ------------------------------------------------------

def test_linha_invalida_na_conferencia_e_marcada_e_nao_vai_ao_siafi(projeto):
    """A pessoa pode ter mexido na conferência entre uma execução e outra."""
    projeto.interrompida(escrever_planilha(projeto.conferencia / 'interrompida.xlsx', [
        linha(Progresso='Ok - 1'), linha(valor='abc'), linha(valor=300)]))
    em = EmuladorFalso(roteiro_login() + roteiro_linha_ok('2026000003'))

    assert executar(projeto.cfg, Fabrica(em)) == 0

    feito, invalida, enviada = projeto.progresso(projeto.conferencia / 'interrompida.xlsx')
    assert feito == 'Ok - 1'
    assert invalida.startswith('Linha inválida: Valor deve conter um número')
    assert enviada == 'Ok - 2026000003'


def test_conferencia_pendente_que_o_robo_nao_interrompeu_nao_vai_ao_siafi(projeto):
    """Deixada pela versão anterior, ou mexida à mão: linhas em branco podem já
    estar no SIAFI."""
    deixada = escrever_planilha(projeto.conferencia / 'deixada.xlsx',
                                [linha(Progresso='Ok - 1'), linha()])
    fabrica = Fabrica()

    assert executar(projeto.cfg, fabrica) == 0

    assert fabrica.criados == []
    assert projeto.progresso(deixada) == ['Ok - 1', '']


def test_nada_pendente_nao_abre_o_siafi(projeto):
    escrever_planilha(projeto.conferencia / 'feita.xlsx', [linha(Progresso='Ok - 1')])
    fabrica = Fabrica()

    assert executar(projeto.cfg, fabrica) == 0
    assert fabrica.criados == []


def test_nao_roda_com_outra_execucao_em_andamento(projeto):
    entrada_com(projeto, linha())
    trava = arquivos.travar_execucao()
    fabrica = Fabrica()

    assert executar(projeto.cfg, fabrica) == 10

    assert fabrica.criados == []
    trava.close()


# --- tradução do retorno ---------------------------------------------------------------

def test_registro_efetuado_vira_ok_com_o_numero_do_documento():
    assert traduzir_progresso(MSG_REGISTRO, '2026000123') == 'Ok - 2026000123'
    assert traduzir_progresso(MSG_REGISTRO, '') == 'Ok'


def test_mensagem_conhecida_vira_texto_amigavel():
    assert traduzir_progresso(
        '0139- VALOR A DESCENTRALIZAR MAIOR QUE SALDO APROVADO.'
    ) == 'Valor a descentralizar maior que o saldo aprovado'
    assert traduzir_progresso(
        'Z03-SIAFI INDISPONIVEL PARA ATUALIZACAO DE DADOS (123)'
    ) == 'SIAFI indisponível para atualização, tente mais tarde'


def test_mensagem_desconhecida_nao_e_escondida_nem_vira_ok():
    assert traduzir_progresso('9999- MENSAGEM NOVA DO SIAFI') == '9999- MENSAGEM NOVA DO SIAFI'


@pytest.mark.parametrize('retorno', ['', '   ', None])
def test_linha_enviada_nunca_fica_com_progresso_em_branco(retorno):
    """Em branco ela seria enviada de novo na execução seguinte."""
    assert traduzir_progresso(retorno) == PROGRESSO_SEM_RETORNO


def test_valor_e_convertido_para_centavos_sem_erro_de_ponto_flutuante():
    valores = {'Orientacao': 'Aprovar', 'Tipo de Descentralizacao': 'Global',
               'UE_Beneficiada': 1500008, 'Fonte': 10, 'Procedencia': 1,
               'Elemento 92': 'N', 'Acao': 2500, 'IAG': 0,
               'Natureza_Despesa_Elemento': 339039, 'Valor': 1234.57}

    data_row = descentralizacao.montar_data_row(valores, '1501')

    assert data_row['valor'] == 123457
    assert (data_row['categoria'], data_row['grupo'], data_row['modalidade'],
            data_row['elemento']) == ('3', '3', '90', '39')
    assert (data_row['item'], data_row['uo_financiadora']) == ('0', '0')
    assert descentralizacao.formatar_valor(123457) == 'R$ 1.234,57'


# --- encerramento do emulador -------------------------------------------------------------

def test_emulador_que_nao_encerra_direito_e_fechado_a_forca():
    """Sem isso o processo do s3270 ficava pendurado e o py3270 tentava de
    novo ao descartar o objeto, jogando um traceback solto na janela."""
    from emulador import encerrar_emulador

    class Processo:
        fechado = False

        def close(self):
            self.fechado = True

    class SessaoCaida:
        is_terminated = False

        def __init__(self):
            self.app = Processo()

        def terminate(self):
            raise ValueError('expected "ok" or "error" result')

    em = SessaoCaida()

    encerrar_emulador(em)          # não propaga

    assert em.app.fechado and em.is_terminated
    encerrar_emulador(None)        # sem emulador, nada a fazer
