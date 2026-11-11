# Automação SIAFI — Descentralização de Cota com py3270

Automação das operações de **descentralização de cota orçamentária** no SIAFI (Sistema Integrado de Administração Financeira) utilizando Python e emulação de terminal TN3270, desenvolvido para a Cidade Administrativa de Minas Gerais.

> Para o passo a passo de uso por quem não é da área técnica, veja o **[RUNBOOK.md](RUNBOOK.md)**.

---

## Sobre o projeto

O SIAFI roda em um terminal TN3270. Este projeto usa a biblioteca **py3270** para controlar o emulador **x3270/s3270** via Python, automatizando a aprovação e a anulação de descentralizações de cota orçamentária, eliminando a interação manual com o terminal.

---

## Funcionalidades

- Validação e consolidação de várias planilhas de descentralização em um único arquivo (`consolida.py`)
- Login automático no SIAFI com tratamento de telas de aviso e de senha expirada
- Aprovação e anulação de descentralização de cota (global e amarrada)
- Captura do retorno do SIAFI (sucesso ou erro) para cada operação, gravado na coluna `Progresso`
- Se parar antes de enviar qualquer linha, as planilhas voltam para a pasta de entrada
- Se parar no meio, a conferência volta para a pasta com o que já foi feito e a execução seguinte continua de onde parou

---

## Instalação automática (Windows + WSL)

Para uso em produção no Windows, os scripts de instalação cuidam de tudo (instalam o WSL/Ubuntu, clonam o repositório, criam o `venv` e coletam as credenciais):

1. `instalar.bat` — primeira instalação (instala WSL/Ubuntu e configura o ambiente).
2. `robo.bat` — execução do dia a dia (confere o ambiente, atualiza o robô, consolida as planilhas e roda a descentralização).
3. `verificar.bat` — diagnóstico: lista o que falta para o robô rodar, sem alterar nada.

Os `.bat` apenas chamam os respectivos `.ps1`, que executam o restante dentro do Ubuntu. Detalhes de uso no **[RUNBOOK.md](RUNBOOK.md)**; para instalar à mão em máquina com proxy, veja o **[INSTALACAO_MANUAL.md](INSTALACAO_MANUAL.md)**.

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
UNIDADE_EXECUTORA=1500008
UNIDADE_ORCAMENTARIA=1501

# Pasta-raiz "Projeto de Descentralização" (Windows, via /mnt/c).
PASTA_WINDOWS=/mnt/c/Users/SEU_USUARIO/OneDrive - CAMG/.../Projeto de Descentralização
# Pasta de trabalho local (Linux) — normalmente a pasta data/ deste repositório.
PASTA_LINUX=/home/SEU_USUARIO/code/splor-mg/siafi-automacao-descentralizacao/data

# Opcional: false roda sem abrir a janela do SIAFI (quando não há WSLg).
#SIAFI_VISIVEL=true
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

# 2. Valida as entradas, arquiva a conferência anterior, consolida em
#    "Conferencia/Conferencia Arquivo Robo DD.MM.xlsx" e move as entradas
#    para "Realizados/Remanejamento Realizados". Só siga se o código de saída for 0.
python consolida.py

# 3. Traz o arquivo de conferência para PASTA_LINUX, loga no SIAFI, processa
#    cada linha gravando o resultado, e devolve o arquivo para "Conferencia".
python siafi_automacao/descentralizacao.py
```

O resultado de cada operação fica na coluna `Progresso` do arquivo `Conferencia Arquivo Robo DD.MM.xlsx`. Linhas que já tenham `Progresso` preenchido são puladas. Rodando mais de uma vez no mesmo dia, os arquivos arquivados ganham ` (1)`, ` (2)`… para nada ser sobrescrito.

### Quando a execução não vai até o fim

| Onde parou | O que o robô faz | O que fazer |
|---|---|---|
| Na validação das planilhas | Lista todos os erros; nada é movido | Corrigir as planilhas e rodar de novo |
| Antes de enviar a primeira linha (sem conexão, senha expirada, login recusado, `.env` incompleto) | Desfaz a consolidação: as planilhas voltam para `Remanejados` e a conferência anterior volta para `Conferencia` | Resolver o problema e rodar de novo |
| No meio das linhas | Devolve a conferência para `Conferencia` com o que já foi feito. A linha em curso fica como `INTERROMPIDA - VERIFICAR NO SIAFI`; as seguintes ficam em branco | Conferir no SIAFI a linha marcada e rodar de novo **sem planilha nova**: o robô retoma as linhas em branco |
| Janela fechada / computador desligado no meio | Na execução seguinte a conferência é trazida de volta da pasta local e retomada do mesmo jeito | Rodar de novo |

Só é retomada sozinha a conferência que o próprio robô devolveu interrompida (registrada em `data/.retomaveis`), se tiver sido mexida nos últimos 7 dias (`RETOMADA_MAX_DIAS`) e se **não** houver planilha nova na pasta de entrada. Uma conferência com linhas em branco que tenha ficado na pasta de outro jeito (deixada pela versão anterior do robô, por exemplo) não é executada sozinha: parte dessas linhas pode já estar no SIAFI. Chegando planilha nova, a conferência antiga é arquivada e o robô avisa quantas linhas dela ficaram sem executar. Duas execuções ao mesmo tempo são recusadas (código de saída 10).

---

## Estrutura do projeto

```
siafi-automacao-descentralizacao/
│
├── consolida.py                      # Valida e consolida as planilhas de "Remanejados" em "Conferencia"
├── siafi_automacao/
│   ├── descentralizacao.py           # Login + processamento da conferência (entrada principal)
│   ├── fluxo_desc.py                 # Telas do SIAFI comuns à aprovação e à anulação
│   ├── fluxo_aprovar_desc.py         # Aprovação: opção do menu e mensagens de recusa
│   ├── fluxo_anular_desc.py          # Anulação: opção do menu e mensagens de recusa
│   ├── validacao.py                  # Regras de preenchimento de uma linha
│   ├── arquivos.py                   # Movimentação entre as pastas, manifesto e trava de execução
│   ├── emulador.py                   # Conexão, espera do teclado e leitura da tela do 3270
│   └── novidades.py                  # Aviso de atualização na janela, uma vez por computador
├── tests/                            # Testes (pytest), com um SIAFI de mentira
├── data/                             # Pasta de trabalho local (PASTA_LINUX) durante o processamento
├── Descentralizacao de Cota Orcamentaria.xlsx   # Planilha modelo
├── NOVIDADES.txt                     # Aviso de atualização mostrado aos órgãos na janela do robô
├── requirements.txt                  # Dependências Python
├── requirements-dev.txt              # Dependências para rodar os testes
├── setup.sh                          # Provisionamento do ambiente Ubuntu/WSL
├── instalar.bat / instalar.ps1       # Instalação no Windows
├── robo.bat / robo.ps1               # Execução no dia a dia
├── verificar.bat / .ps1 / .sh        # Diagnóstico do ambiente (não altera nada)
├── instalador.nsi                    # Script NSIS que gera o Automação_Descentralização.exe
├── RUNBOOK.md                        # Manual passo a passo para o usuário final
├── INSTALACAO_MANUAL.md              # Instalação à mão em máquina com proxy
└── README.md                         # Este arquivo
```

---

## Avisar os órgãos sobre uma atualização

Quem usa o robô são os órgãos, e a janela do `robo.bat` é o único canal com eles. Na primeira execução depois de o robô se atualizar, a janela mostra o texto do [NOVIDADES.txt](NOVIDADES.txt) por alguns segundos, uma vez só em cada computador.

Para avisar de uma mudança, troque o texto desse arquivo no mesmo commit da mudança: texto diferente aparece de novo, uma vez, em cada computador (o registro fica em `data/.novidades_vistas`). Escreva para quem usa o robô, em poucas linhas de no máximo 76 caracteres; linhas começadas por `#` não aparecem, e arquivo sem texto não mostra aviso. Mudança que não afeta quem usa não precisa de aviso.

O aviso é mostrado pelo `consolida.py`, e não pelo `robo.ps1`, porque o `robo.ps1` em execução é sempre o de antes do `git pull`.

---

## Testes

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
```

Os testes não tocam no SIAFI, no `.env` nem nas pastas de verdade: usam pastas temporárias e um emulador falso (`tests/emulador_falso.py`). `tests/test_fluxos.py` trava, tecla a tecla, o que é digitado no terminal.

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
- Por padrão o robô abre a janela gráfica do terminal (`x3270`) — exige WSLg. Para rodar sem ela, coloque `SIAFI_VISIVEL=false` no `.env` (usa o `s3270`). Não altere o código para isso: um arquivo modificado localmente faz o `git pull` automático parar de funcionar.
- O robô só funciona dentro da rede da SEPLAG (ou via VPN).

---

## Referências

- [py3270 no PyPI](https://pypi.org/project/py3270/)
- [x3270 — IBM 3270 Terminal Emulator](http://x3270.bgp.nu/)
