"""Um SIAFI de mentira para os testes.

O emulador falso registra tudo o que o robô "digita" e mostra as telas de um
roteiro: cada tecla de envio (Enter, PF3, PF5...) avança para a tela seguinte.
Uma tela é um dicionário {linha: texto}; o texto começa na coluna 1. No lugar
de uma tela, o roteiro pode trazer uma exceção — ela é levantada naquela
tecla, simulando o SIAFI caindo ou travando o teclado.
"""

MSG_REGISTRO = '0011-REGISTRO EFETUADO.'
MSG_CONFIRMAR = '0017-TECLE PF5 PARA CONFIRMAR OU PF2 PARA ANULAR.'

VAZIA = {}


def tela_logon_ok():
    return {1: ' ' * 12 + 'Logon executado com sucesso'}


def tela_unidade_executora():
    return {22: ' ' * 10 + 'Unidade Executora'}


def roteiro_login():
    """Telas mostradas a cada tecla, do envio da senha até o menu de
    descentralização."""
    return [
        VAZIA,                      # Enter com usuário e senha -> tela de aviso
        tela_logon_ok(),            # Enter -> logon efetuado
        VAZIA,                      # Enter com o sistema -> tela de aviso
        tela_unidade_executora(),   # Enter -> pede a unidade executora
        VAZIA,                      # Enter com a UE -> menu principal
        VAZIA,                      # 03 -> movimentação orçamentária
        VAZIA,                      # 03 -> descentralização de cota
    ]


def roteiro_linha_ok(nr_doc='2026000123'):
    """Telas de uma linha efetivada, da opção do menu até a volta a ele."""
    return [
        VAZIA,                                  # 01/02-1 -> tela de classificação
        VAZIA,                                  # Enter -> tela do valor
        VAZIA,                                  # Enter -> justificativa
        {1: MSG_CONFIRMAR},                     # Enter -> pede confirmação
        {1: MSG_CONFIRMAR},                     # PF5
        {1: MSG_REGISTRO,                       # PF5 -> registrado
         7: f'   Nr. Documento Global: {nr_doc}   '},
        VAZIA,                                  # PF3 -> menu
    ]


def roteiro_linha_recusada_na_classificacao(mensagem):
    return [
        VAZIA,              # 01/02-1 -> tela de classificação
        {1: mensagem},      # Enter -> o SIAFI recusa
        VAZIA,              # PF3 -> menu
    ]


class EmuladorFalso:
    def __init__(self, roteiro=(), visible=False, falha_ao_conectar=None):
        self.roteiro = list(roteiro)
        self.visible = visible
        self.falha_ao_conectar = falha_ao_conectar
        self.tela = VAZIA
        self.chamadas = []
        self.terminado = False

    # --- o que o robô faz -------------------------------------------------
    def connect(self, host):
        self.chamadas.append(('connect', host))
        if self.falha_ao_conectar is not None:
            raise self.falha_ao_conectar

    def wait_for_field(self):
        self.chamadas.append(('wait_for_field',))

    def fill_field(self, linha, coluna, texto, tamanho):
        assert len(texto) <= tamanho, f'{texto!r} não cabe em {tamanho}'
        self.chamadas.append(('fill_field', linha, coluna, texto, tamanho))

    def send_enter(self):
        self.chamadas.append(('send_enter',))
        self._avancar()

    def send_pf(self, numero):
        self.chamadas.append(('send_pf', numero))
        self._avancar()

    def exec_command(self, comando):
        self.chamadas.append(('exec_command', comando))

    def terminate(self):
        self.terminado = True

    # --- o que o robô lê (não entra em 'chamadas') -------------------------
    def string_get(self, linha, coluna, tamanho):
        texto = self.tela.get(linha, '').ljust(80)
        return texto[coluna - 1:coluna - 1 + tamanho]

    def string_found(self, linha, coluna, texto):
        return self.string_get(linha, coluna, len(texto)) == texto

    # --- apoio --------------------------------------------------------------
    def _avancar(self):
        if not self.roteiro:
            raise AssertionError('o robô teclou além do fim do roteiro')
        proxima = self.roteiro.pop(0)
        if isinstance(proxima, BaseException):
            raise proxima
        self.tela = proxima

    def digitado(self):
        """Só o que foi enviado ao SIAFI: campos preenchidos e teclas."""
        return [c for c in self.chamadas
                if c[0] in ('fill_field', 'send_enter', 'send_pf')]


class Fabrica:
    """Entrega emuladores falsos no lugar do py3270.Emulator, na ordem dada."""

    def __init__(self, *emuladores):
        self.fila = list(emuladores)
        self.criados = []

    def __call__(self, visible=False):
        em = self.fila.pop(0)
        em.visible = visible
        self.criados.append(em)
        return em
