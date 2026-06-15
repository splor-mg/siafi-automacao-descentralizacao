# Automação SIAFI — Descentralização de Cota com py3270

Automação das operações de **descentralização de cota orçamentária** no SIAFI (Sistema Integrado de Administração Financeira) utilizando Python e emulação de terminal TN3270, desenvolvido para a Cidade Administrativa de Minas Gerais.

> Para o passo a passo de uso por quem não é da área técnica, veja o **[RUNBOOK.md](RUNBOOK.md)**.

---

## Sobre o projeto

O SIAFI roda em um terminal TN3270. Este projeto usa a biblioteca **py3270** para controlar o emulador **x3270/s3270** via Python, automatizando a aprovação e a anulação de descentralizações de cota orçamentária, eliminando a interação manual com o terminal.

---

## Funcionalidades

- Consolidação de várias planilhas de descentralização em um único arquivo (`consolida.py`)
- Login automático no SIAFI com tratamento de telas de aviso
- Leitura da planilha consolidada com os dados das operações
- Aprovação de descentralização de cota (global e amarrada)
- Anulação de descentralização de cota
- Captura do retorno do SIAFI (sucesso ou erro) para cada operação, gravado na coluna `Progresso`

---

## Instalação automática (Windows + WSL)

Para uso em produção no Windows, os scripts de instalação cuidam de tudo (instalam o WSL/Ubuntu, clonam o repositório, criam o `venv` e coletam as credenciais):

1. `instalar.bat` — primeira instalação (instala WSL/Ubuntu e configura o ambiente).
2. `robo.bat` — execução do dia a dia (consolida as planilhas e roda a descentralização).

Os `.bat` apenas chamam os respectivos `.ps1` (`instalar.ps1`, `robo.ps1`), que por sua vez executam o `setup.sh` dentro do Ubuntu. Detalhes de uso no **[RUNBOOK.md](RUNBOOK.md)**.

---

## Instalação manual (Ubuntu / WSL)

### Dependências do sistema

```bash
sudo apt update
sudo apt install x3270 s3270 python3 python3-pip python3-venv
```

### Clonar o repositório e criar o ambiente

```bash
git clone https://github.com/splor-mg/siafi-automacao-descentralizacao.git
cd siafi-automacao-descentralizacao

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuração (`.env`)

Copie o `.env.example` para `.env` e preencha (veja [.env.example](.env.example)):

```
USUARIO=seu_usuario
SENHA=sua_senha
UNIDADE_EXECUTORA=1451

# Pasta no OneDrive (Windows, via /mnt/c) onde as planilhas são colocadas;
# o consolidado processado é devolvido aqui ao final.
PASTA_WINDOWS=/mnt/c/Users/SEU_USUARIO/OneDrive - CAMG/.../Descentralizacao de cota
# Pasta de trabalho local (Linux) — normalmente a pasta data/ deste repositório.
PASTA_LINUX=/home/SEU_USUARIO/code/splor-mg/siafi-automacao-descentralizacao/data
```

> O sistema de acesso é fixo (`simg`) no código, por isso não vai no `.env`.

`PASTA_WINDOWS` é a pasta-raiz **`Projeto de Descentralização`** (pode estar no OneDrive ou não). Dentro dela devem existir as subpastas:

```
Projeto de Descentralização/
├── Remanejados (Insira seu arquivo aqui)/   # entradas a processar
├── Conferencia/                             # consolidado gerado/processado
└── Realizados/
    ├── Remanejamento Realizados/            # entradas já consolidadas
    └── Conferencia Realizados/              # conferências de dias anteriores
```

---

## Como usar

```bash
source venv/bin/activate

# 1. Coloque as planilhas na subpasta "Remanejados (Insira seu arquivo aqui)"
#    de PASTA_WINDOWS, cada uma com a aba "Execucao".

# 2. Arquiva a conferência anterior, consolida as entradas em
#    "Conferencia/Conferencia Arquivo Robo DD.MM.xlsx" e move as entradas
#    para "Realizados/Remanejamento Realizados".
python consolida.py

# 3. Traz o arquivo de conferência para PASTA_LINUX, loga no SIAFI, processa
#    cada linha gravando o resultado, e devolve o arquivo para "Conferencia".
python siafi_automacao/descentralizacao.py
```

O resultado de cada operação fica na coluna `Progresso` do arquivo `Conferencia Arquivo Robo DD.MM.xlsx`. Linhas que já tenham `Progresso` preenchido são puladas. Rodando mais de uma vez no mesmo dia, os arquivos arquivados ganham ` (1)`, ` (2)`… para nada ser sobrescrito.

---

## Estrutura do projeto

```
siafi-automacao-descentralizacao/
│
├── consolida.py                      # Consolida as planilhas de "Remanejados" em "Conferencia"
├── siafi_automacao/
│   ├── descentralizacao.py           # Login + processamento do consolidado (entrada principal)
│   ├── fluxo_aprovar_desc.py         # Fluxo de aprovação no terminal SIAFI
│   └── fluxo_anular_desc.py          # Fluxo de anulação no terminal SIAFI
├── data/                             # Pasta de trabalho local (PASTA_LINUX) durante o processamento
├── requirements.txt                  # Dependências Python
├── setup.sh                          # Provisionamento do ambiente Ubuntu/WSL
├── instalar.bat / instalar.ps1       # Instalação no Windows
├── robo.bat / robo.ps1               # Execução no dia a dia
├── RUNBOOK.md                        # Manual passo a passo para o usuário final
└── README.md                         # Este arquivo
```

---

## Principais bibliotecas utilizadas

| Biblioteca | Descrição |
|------------|-----------|
| `py3270` | Interface Python para o emulador x3270/s3270 |
| `pandas` | Leitura/escrita e manipulação das planilhas |
| `openpyxl` | Leitura e escrita de planilhas Excel (.xlsx) e formatação |
| `python-dotenv` | Carregamento das credenciais do arquivo `.env` |

---

## Observações

- O emulador `x3270` precisa estar instalado e disponível no PATH para o py3270 funcionar.
- Em modo `visible=True` (padrão em `descentralizacao.py`) o script abre a janela gráfica do terminal — exige WSLg. Para rodar em segundo plano, altere para `visible=False` (usa o `s3270`).
- O robô só funciona dentro da rede da SEPLAG (ou via VPN).

---

## Referências

- [py3270 no PyPI](https://pypi.org/project/py3270/)
- [x3270 — IBM 3270 Terminal Emulator](http://x3270.bgp.nu/)
