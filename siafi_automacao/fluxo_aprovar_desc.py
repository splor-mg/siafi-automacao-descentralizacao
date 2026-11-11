"""Aprovação de descentralização de cota: opção 01-1 do menu."""

from fluxo_desc import lancar

# Mensagens com que o SIAFI recusa a linha logo na primeira tela.
RECUSAS_CLASSIFICACAO = (
    "E90 - SALDO ZERADO NA CONTA",
    "0139- PROJ/ATIV OU FONTE/PROC./IAG INEXISTENTE PARA UO",
    "0101- NATUREZA DESPESA INEXISTENTE(S).",
    "0101- GRUPO DESPESA INEXISTENTE(S).",
    "0139- PROGRAMA DE TRABALHO NAO ENCONTRADO PARA GM/FP.",
    "0109-INFORME NATUREZA DE DESPESA COMPLETA.",
)

# Mensagens com que o SIAFI recusa a linha depois de informado o valor.
RECUSAS_VALOR = (
    "0139- VALOR A APROVAR MAIOR QUE SALDO DISPONIVEL NO PROJ/ATIV.",
    "0139- PROJ/ATIV OU FONTE/PROC./IAG INEXISTENTE PARA UO",
    "SALDO DE CREDITO ORCAMENTARIO A APROVAR POR PROJ/ATIV ZERADO.",
    "0139- VALOR A DESCENTRALIZAR MAIOR QUE SALDO APROVADO.",
)


def aprovacao(em, data_row):
    """Aprova a descentralização de uma linha. Devolve (retorno, nr_doc)."""
    return lancar(em, data_row, '01', RECUSAS_CLASSIFICACAO, RECUSAS_VALOR)
