"""Proteções que valem para todos os testes.

Nenhum teste pode tocar nas pastas de verdade, no .env, no SIAFI ou na trava
de execução da máquina: os módulos recebem caminhos por parâmetro e aqui o
resto é isolado.
"""
import os
import time

import pandas as pd
import pytest

import arquivos
from validacao import COLUNAS_CONFERENCIA


@pytest.fixture(autouse=True)
def isolamento(tmp_path, monkeypatch):
    # Trava própria: não disputa com um robô rodando de verdade nesta máquina.
    monkeypatch.setenv('SIAFI_LOCK', str(tmp_path / 'robo.lock'))
    # Pasta local própria: o consolida.main() grava nela o registro das
    # novidades vistas, e não pode mexer no data/ de verdade.
    monkeypatch.setenv('PASTA_LINUX', str(tmp_path / 'data'))
    # Os fluxos e o login dormem entre as telas; no teste isso só atrasa.
    monkeypatch.setattr(time, 'sleep', lambda _segundos: None)
    monkeypatch.setenv('MOVER_TENTATIVAS', '2')
    monkeypatch.setenv('MOVER_ESPERA_SEGUNDOS', '0')
    monkeypatch.delenv('RETOMADA_MAX_DIAS', raising=False)


class Projeto:
    """A pasta "Projeto de Descentralização" e a pasta local, num tmp_path."""

    def __init__(self, raiz):
        self.windows = raiz / 'Projeto de Descentralização'
        self.local = raiz / 'data'
        self.remanejados = self.windows / arquivos.SUB_REMANEJADOS
        self.conferencia = self.windows / arquivos.SUB_CONFERENCIA
        self.realizados_rem = self.windows / arquivos.SUB_REALIZADOS_REMANEJAMENTO
        self.realizados_conf = self.windows / arquivos.SUB_REALIZADOS_CONFERENCIA
        self.em_processamento = self.local / arquivos.SUB_EM_PROCESSAMENTO
        self.manifesto = self.local / arquivos.NOME_MANIFESTO
        self.registro = self.local / arquivos.NOME_RETOMAVEIS
        for pasta in (self.remanejados, self.conferencia, self.realizados_rem,
                      self.realizados_conf, self.local):
            pasta.mkdir(parents=True)

    @property
    def cfg(self):
        return {
            'usuario': 'M1234567',
            'senha': 'segredo1',
            'unidade_executora': '1500008',
            'unidade_orcamentaria': '1501',
            'pasta_windows': str(self.windows),
            'pasta_local': str(self.local),
            'host': 'siafi.teste',
            'visivel': False,
            'conexao_tentativas': 2,
        }

    def interrompida(self, caminho):
        """Registra a conferência como devolvida interrompida pelo robô — o
        estado em que ela pode ser retomada sem planilha nova."""
        arquivos.marcar_retomavel(str(self.registro), str(caminho))
        return caminho

    def retomaveis(self):
        return arquivos.retomaveis(str(self.registro))

    def nomes(self, pasta):
        return sorted(p.name for p in pasta.iterdir() if p.is_file())

    def progresso(self, caminho):
        """A coluna Progresso de uma conferência, com '' no lugar de vazio."""
        df = pd.read_excel(caminho, sheet_name=arquivos.ABA)
        return ['' if pd.isna(v) else str(v) for v in df['Progresso']]


@pytest.fixture
def projeto(tmp_path):
    return Projeto(tmp_path)


def linha(orientacao='Aprovar', tipo='Global', valor=1500.50, **outros):
    """Uma linha válida da planilha de entrada; 'outros' troca colunas."""
    base = {
        'Orientacao': orientacao,
        'UE_Beneficiada': 1500008,
        'Tipo de Descentralizacao': tipo,
        'Fonte': 10,
        'Procedencia': 1,
        'Elemento 92': 'N',
        'Acao': 2500,
        'IAG': 0,
        'Natureza_Despesa_Elemento': 339039,
        'Item': 5 if tipo == 'Amarrado' else None,
        'UO_Financiadora': None,
        'Valor': valor,
        'Progresso': None,
    }
    base.update(outros)
    return base


def escrever_planilha(caminho, linhas, aba=arquivos.ABA):
    """Grava uma planilha de entrada (ou uma conferência) com as linhas dadas."""
    df = pd.DataFrame(linhas, columns=COLUNAS_CONFERENCIA)
    df.to_excel(caminho, sheet_name=aba, index=False)
    return caminho


def envelhecer(caminho, dias):
    """Faz o arquivo parecer ter sido mexido pela última vez há 'dias' dias."""
    quando = time.time() - dias * 86400
    os.utime(caminho, (quando, quando))
