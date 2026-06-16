# Manual do Robô de Descentralização de Cota SIAFI

Este manual ensina, passo a passo, como usar o robô. **Você não precisa saber nada de computador.** Basta seguir cada passo na ordem, do começo ao fim. Cada passo diz exatamente o que fazer.

---

## O que o robô faz

O robô junta todas as planilhas de **descentralização de cota** que você colocar na pasta `Remanejados`, monta uma planilha única (a "conferência") na pasta `Conferencia`, entra no SIAFI sozinho e faz cada operação de aprovação ou anulação, uma por uma. No final, ele preenche essa conferência dizendo o que deu certo e o que deu errado.

---

# PARTE 1 — Uso no dia a dia

> Use esta parte **depois** que o robô já estiver instalado no computador.
> Se for a **primeira vez** neste computador, vá antes para a **PARTE 2** (mais abaixo).

## Passo 1 — Conferir se você está na rede da SEPLAG

O robô só funciona dentro da rede da SEPLAG.

- Se você está **no computador do trabalho, na SEPLAG** → tudo certo, continue.
- Se você está **em casa ou fora** → ligue a **VPN** antes de continuar.

## Passo 2 — Colocar as planilhas na pasta "Remanejados"

1. Abra a pasta **Projeto de Descentralização** (no OneDrive ou onde ela estiver no seu computador — é a mesma configurada na instalação).
2. Entre na subpasta **`Remanejados (Insira seu arquivo aqui)`**.
3. Copie ou arraste para dentro dela **os arquivos Excel** de descentralização que quer processar.

**Importante:** feche os arquivos Excel antes de continuar. Eles não podem estar abertos.

> Cada planilha precisa ter a aba **`Execucao`**, com as colunas de sempre (`Orientacao`, `UE_Beneficiada`, `Valor`, etc.).

## Passo 3 — Ligar o robô

1. Abra a pasta onde está o robô (a pasta com os arquivos que você recebeu).
2. Procure o arquivo chamado **robo** (com um ícone de engrenagem). O nome completo é `robo.bat`.
3. **Clique duas vezes seguidas** (rápido) em cima dele.

## Passo 4 — Esperar o robô trabalhar

- Uma **janela preta** vai abrir na tela. É normal. **Não feche.**
- A primeira coisa que ela mostra é `Atualizando o robo...` — o robô se atualiza sozinho com a versão mais recente antes de rodar. É normal.
- Pode abrir também a **tela do SIAFI** (um terminal). **Não feche e não clique nessa tela** — é o robô "digitando" sozinho.
- Primeiro o robô junta todas as planilhas da pasta `Remanejados` em uma só e a coloca na pasta `Conferencia`.
- Em seguida ele entra no SIAFI e faz cada linha, uma por uma. Na janela preta vão aparecendo os resultados.

> **Você pode usar o computador normalmente enquanto o robô trabalha** (e-mail, navegador, planilhas, etc.). O robô controla o SIAFI "por dentro", então digitar ou clicar em **outros** programas **não atrapalha**. A única regra é: **não feche nem clique nas janelas do próprio robô** (a janela preta e a tela do SIAFI).

## Passo 5 — Conferir o resultado

1. Quando o robô terminar, abra a subpasta **`Conferencia`** (dentro de `Projeto de Descentralização`).
2. Abra o arquivo **`Conferencia Arquivo Robo DD.MM.xlsx`** (onde `DD.MM` é a data de hoje) — é a planilha já processada que o robô devolveu.
3. Olhe a coluna **Progresso**: ela mostra, linha por linha, o que deu certo (`Ok`) e o que deu errado.

> - As planilhas que você colocou em `Remanejados` são movidas pelo robô para `Realizados\Remanejamento Realizados`, para não serem processadas de novo.
> - A cada execução, a conferência anterior que estava em `Conferencia` é movida para `Realizados\Conferencia Realizados`. Se você rodar mais de uma vez no mesmo dia, os arquivos antigos ganham ` (1)`, ` (2)`... no nome, para nada ser sobrescrito.

**Acabou.** Para rodar de novo, é só repetir a PARTE 1 desde o Passo 1.

---

# PARTE 2 — Primeira vez neste computador

> Faça esta parte **só uma vez**, na primeira vez que usar o robô em um computador novo.
> Depois disso, use sempre a PARTE 1.

A primeira instalação tem **2 etapas**, com **um reinício no meio**. Você vai clicar no `instalar.bat` **duas vezes** (antes e depois de reiniciar).

## Etapa A — Instalar o "motor" do robô e reiniciar

> Se ao clicar no `instalar.bat` ele já pular direto para pedir as credenciais do SIAFI (sem falar em instalar WSL/Ubuntu), o motor já está instalado — vá direto para a **Etapa B**.

1. Abra a pasta do robô e clique duas vezes em **instalar** (`instalar.bat`).
2. Vai aparecer uma janela do Windows pedindo permissão de administrador. Clique em **Sim**.
3. **Se você estiver na rede da SEPLAG**, pode aparecer um pedido das credenciais do **proxy** (para baixar os programas):
   - **Usuário do proxy:** a sua **matrícula**.
   - **Senha do proxy:** a senha que você usa para a internet/rede da SEPLAG *(não aparece ao digitar)*.
4. **Espere** o download e a instalação do WSL e do Ubuntu. Pode demorar **vários minutos**. Não feche nada.
5. No final, aparece a mensagem pedindo para **reiniciar o computador**.
6. Salve tudo o que estiver aberto e **reinicie** (Menu Iniciar → botão de ligar → Reiniciar).

## Etapa B — Criar o usuário do Ubuntu e configurar (depois de reiniciar)

1. Depois de reiniciar, clique duas vezes em **instalar** (`instalar.bat`) **de novo**.
2. Uma **janela escura** vai pedir para criar o **usuário e a senha do Ubuntu**:
   - Digite um nome simples (por exemplo `siafi`) e aperte **Enter**.
   - Digite uma senha, **anote em um papel** para não esquecer, e aperte **Enter**. Quando pedir, **repita** a mesma senha.

   > As letras da senha **não aparecem** ao digitar. É normal e proposital. Continue digitando mesmo sem ver.
3. Em seguida o robô começa a se configurar sozinho. Durante isso, ele pode perguntar:

   **a) Proxy** — *"Está na rede da CAMG/PRODEMGE e precisa de proxy? [S/n]"*
   - Se estiver na SEPLAG, aperte **Enter** (Sim) e informe a **matrícula** e a **senha do proxy** de novo.

   **b) Credenciais do SIAFI** — uma de cada vez:

   | Quando aparecer | Digite |
   |-----------------|--------|
   | `USUARIO` | O seu login do SIAFI |
   | `SENHA` | A sua senha do SIAFI *(não aparece ao digitar)* |
   | `UNIDADE_EXECUTORA` | O código da sua unidade. Exemplo: `1451` |

   **c) Pasta do projeto** — *"Qual o caminho que irá ser utilizado no projeto?"*
   - Cole a pasta **onde** o projeto deve ficar (o robô cria a `Projeto de Descentralização` e as subpastas lá dentro). Exemplo:

     ```
     C:\Users\SEU_USUARIO\OneDrive - CAMG\General\@dcmefo\2026
     ```

   - Se aparecer uma **sugestão**, é só apertar **Enter** para aceitar.
4. No final, aparece a mensagem de **configuração concluída** — e a pasta do projeto já fica criada e pronta.

> A partir daí, é só usar a **PARTE 1** sempre que precisar.

---

# A estrutura de pastas (criada automaticamente na instalação)

O robô trabalha sempre dentro de **uma pasta-raiz chamada `Projeto de Descentralização`**. Você **não precisa criar essas pastas à mão**: na Etapa B da instalação, ao responder *"Qual o caminho que irá ser utilizado no projeto?"*, o próprio instalador cria a `Projeto de Descentralização` e todas as subpastas no lugar que você indicar.

Essa pasta pode ficar **em qualquer lugar** do computador — dentro do OneDrive ou não. O que muda de um computador para outro é **só onde ela está**. Exemplos de caminho que você pode informar na instalação (o caminho-pai, sem a `Projeto de Descentralização`):

```
C:\Users\SEU_USUARIO\OneDrive - CAMG\General\@dcmefo\2026
C:\Users\SEU_USUARIO\OneDrive - CAMG\@splor\@dcmefo\2026
C:\Users\SEU_USUARIO
```

A estrutura que o instalador cria fica assim:

```
Projeto de Descentralização\
├── Remanejados (Insira seu arquivo aqui)\   ← você coloca aqui as planilhas a processar
├── Conferencia\                             ← o robô coloca aqui a planilha final
└── Realizados\
    ├── Remanejamento Realizados\            ← para onde vão as planilhas já consolidadas
    └── Conferencia Realizados\              ← para onde vão as conferências de dias anteriores
```

Como o caminho fica salvo no arquivo `.env` de cada computador, dá para **clonar o robô em vários computadores**: em cada um, na instalação, basta informar onde a pasta do projeto deve ser criada naquela máquina.

---

# O que significa a coluna "Progresso"

Quando o robô termina, ele escreve o resultado de cada linha na coluna **Progresso** do arquivo `Conferencia Arquivo Robo DD.MM.xlsx`:

| O que está escrito | O que significa |
|--------------------|-----------------|
| `Ok` | Deu tudo certo |
| `Saldo zerado na conta` | Não tinha saldo para fazer a operação |
| `Proj/Ativ ou Fonte/Proc./IAG inexistente para a UO` | Uma classificação não foi encontrada |
| `Natureza de despesa inexistente` | A natureza de despesa informada não existe |
| `Grupo de despesa inexistente` | O grupo de despesa está errado |
| `Programa de trabalho não encontrado para GM/FP` | Não há programa de trabalho para a combinação informada |
| `Informe a natureza de despesa completa` | Faltou completar a natureza de despesa |
| `Não existe descentralização para Proj/Ativ ou Fonte/Proc./IAG` | Não há descentralização para aquela classificação |
| `Saldo inexistente a anular para Proj/Ativ` | Não tinha saldo para anular |
| `Valor a aprovar maior que o saldo disponível` | Não tinha saldo suficiente para aprovar |
| `Saldo de crédito a aprovar zerado` | O saldo a aprovar estava zerado |
| `Valor a descentralizar maior que o saldo aprovado` | O valor pedido passa do saldo aprovado |
| `Valor informado além do valor descentralizado` | O valor passa do que foi descentralizado |

> As linhas que já tinham a coluna Progresso preenchida são **puladas**. O robô só faz as que ainda estão em branco.

---

# Quando algo dá errado

## A janela preta fechou sozinha, sem dizer nada

- Provavelmente um arquivo Excel estava aberto. **Feche o Excel** e tente de novo.
- Ou não havia nenhuma planilha na pasta `Remanejados (Insira seu arquivo aqui)`. Confira o Passo 2 da PARTE 1.

## Apareceu "Nao foi possivel estabelecer conexao com o servidor"

O robô não conseguiu entrar no SIAFI. Confira:
- Você está na rede da SEPLAG ou com a VPN ligada?
- O SIAFI está funcionando no seu navegador?

Feche a janela preta e tente de novo desde o Passo 3.

## Apareceu "Senha expirada" e abriu um arquivo no Bloco de Notas

Sua senha do SIAFI **venceu**. O robô para, avisa, e **abre sozinho o arquivo `.env`** no Bloco de Notas para você atualizar a senha. Faça assim:

1. Entre no **SIAFI manualmente** (do jeito de sempre) e **troque a sua senha** por uma nova.
2. No arquivo `.env` que abriu, ache a linha que começa com `SENHA=` e troque pela **nova senha**.
3. **Salve** o arquivo (Ctrl + S) e feche o Bloco de Notas.
4. Rode o **robo.bat** de novo (PARTE 1).

## Apareceu "Nao foi possivel fazer login apos varias tentativas"

O robô não conseguiu entrar no SIAFI. Confira:
- A `SENHA` no arquivo `.env` está correta? *(veja como abrir o `.env` no item acima)*
- Você está na rede da SEPLAG ou com a VPN ligada?

Se continuar, peça ajuda ao **suporte técnico da DCMEFO**.

## Deu erro de download / proxy durante a instalação

- Confira se digitou certo a **matrícula** e a **senha do proxy**.
- Você precisa estar **na rede da SEPLAG** (ou VPN) para baixar o WSL/Ubuntu.
- Se persistir, chame o **suporte técnico da DCMEFO**.

## Apareceu "ERRO: setup.sh falhou"

Deu um problema na instalação. Pode ser falta de internet ou proxy. Chame o **suporte técnico da DCMEFO**.

## Qualquer outra coisa

Não tente adivinhar. Tire uma **foto da tela** (ou print) e mande para o **suporte técnico da DCMEFO/SEPLAG**.

---

**Dúvidas?** Fale com a equipe técnica da DCMEFO/SEPLAG.
