# Manual do Robô de Descentralização de Cota SIAFI

Este manual ensina, passo a passo, como usar o robô. **Você não precisa saber nada de computador.** Basta seguir cada passo na ordem, do começo ao fim. Cada passo diz exatamente o que fazer.

---

## O que o robô faz

O robô junta todas as planilhas de **descentralização de cota** que você colocar na pasta `Remanejados`, confere se estão preenchidas corretamente, monta uma planilha única (a "conferência") na pasta `Conferencia`, entra no SIAFI sozinho e faz cada operação de aprovação ou anulação, uma por uma. No final, ele preenche essa conferência dizendo o que deu certo e o que deu errado.

Se alguma coisa impedir o robô de trabalhar, ele **não deixa nada pela metade sem avisar**: ou devolve as suas planilhas para a pasta `Remanejados` (quando nada foi feito no SIAFI), ou devolve a conferência mostrando exatamente até onde chegou. Veja **"Quando algo dá errado"** mais abaixo.

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
- Se o robô tiver sido atualizado desde a última vez, aparece um aviso **"O ROBÔ FOI ATUALIZADO"** dizendo o que mudou. Ele fica alguns segundos na tela e depois o robô continua sozinho. Aparece uma vez só.
- Pode abrir também a **tela do SIAFI** (um terminal). **Não feche e não clique nessa tela** — é o robô "digitando" sozinho.
- Primeiro o robô confere e junta todas as planilhas da pasta `Remanejados` em uma só e a coloca na pasta `Conferencia`. Se encontrar algum erro de preenchimento, ele **para aqui**, lista os erros e não mexe em nada (veja "Quando algo dá errado").
- Em seguida ele entra no SIAFI e faz cada linha, uma por uma. Na janela preta vão aparecendo os resultados.
- No final aparece um **resumo**: quantas linhas deram certo, quantas o SIAFI recusou e quantas ficaram por fazer.

> **Você pode usar o computador normalmente enquanto o robô trabalha** (e-mail, navegador, planilhas, etc.). O robô controla o SIAFI "por dentro", então digitar ou clicar em **outros** programas **não atrapalha**. As regras são: **não feche nem clique nas janelas do próprio robô** (a janela preta e a tela do SIAFI), **não abra a planilha da pasta `Conferencia` enquanto ele trabalha** e **não clique no robô uma segunda vez** antes de ele terminar.

## Passo 5 — Conferir o resultado

1. Quando o robô terminar, abra a subpasta **`Conferencia`** (dentro de `Projeto de Descentralização`).
2. Abra o arquivo **`Conferencia Arquivo Robo DD.MM.xlsx`** (onde `DD.MM` é a data de hoje) — é a planilha já processada que o robô devolveu.
3. Olhe a coluna **Progresso**: ela mostra, linha por linha, o que deu certo (`Ok - número do documento`) e o que deu errado. O significado de cada texto está na tabela **"O que significa a coluna Progresso"**, mais abaixo.

> - As planilhas que você colocou em `Remanejados` são movidas pelo robô para `Realizados\Remanejamento Realizados`, para não serem processadas de novo.
> - A cada execução com planilhas novas, a conferência anterior que estava em `Conferencia` é movida para `Realizados\Conferencia Realizados`. Se você rodar mais de uma vez no mesmo dia, os arquivos antigos ganham ` (1)`, ` (2)`... no nome, para nada ser sobrescrito.

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
   | `UNIDADE_EXECUTORA` | O código da sua unidade executora, com 7 dígitos. Exemplo: `1500008` |
   | `UNIDADE_ORCAMENTARIA` | O código da unidade orçamentária da sua unidade, com 4 dígitos. Exemplo: `1501` |

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
| `Ok - 2026...` | Deu tudo certo. O número é o do documento gerado no SIAFI |
| `INTERROMPIDA - VERIFICAR NO SIAFI` | O robô parou no meio desta linha e **não sabe se ela entrou no SIAFI**. Confira no SIAFI. Ela não é refeita sozinha (veja "O robô parou no meio") |
| `SEM RETORNO DO SIAFI - VERIFICAR NO SIAFI` | O robô enviou a linha, mas o SIAFI não devolveu mensagem. Confira no SIAFI se ela entrou |
| `Linha inválida: ...` | A linha está preenchida de um jeito que o robô não aceita (o texto diz a coluna e o problema). Ela **não** foi enviada ao SIAFI |
| `Operação não confirmada no SIAFI` | O SIAFI não aceitou a confirmação final. A operação **não** foi feita |
| `Erro de saldo contábil` | O SIAFI acusou inconsistência na contabilização. A operação **não** foi feita |
| `SIAFI indisponível para atualização, tente mais tarde` | O SIAFI estava fora do ar para gravação. A operação **não** foi feita |
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
>
> Se aparecer na coluna um texto que não está nesta tabela (em geral começando com um número, como `0139- ...`), é a mensagem do SIAFI do jeito que ela veio: a operação **não** foi feita. Mande um print para o suporte técnico da DCMEFO para a mensagem ser incluída na tabela.

---

# Quando algo dá errado

## Apareceu "VALIDAÇÃO ENCONTROU ... PROBLEMA(S). Nada foi consolidado."

Alguma planilha está preenchida de um jeito que o robô não aceita. Ele lista, uma por linha, **o arquivo, a linha do Excel, a coluna e o que encontrou**. Nada foi movido nem enviado ao SIAFI.

1. Abra a planilha indicada (ela continua na pasta `Remanejados`) e corrija os itens da lista.
2. **Salve e feche** o Excel.
3. Rode o robô de novo.

## Apareceu "Nenhuma planilha nova para processar"

Não havia planilha na pasta `Remanejados (Insira seu arquivo aqui)`, nem trabalho interrompido para continuar. Confira o Passo 2 da PARTE 1. A planilha precisa ser um arquivo do Excel no formato `.xlsx`.

## Apareceu "Não foi possível conectar ao SIAFI"

O robô não conseguiu chegar ao SIAFI. **Nada foi feito, e as suas planilhas voltaram para a pasta `Remanejados`.** Confira:
- Você está na rede do governo ou com a VPN ligada?
- O SIAFI está funcionando quando você entra nele do jeito de sempre?

Depois é só rodar o robô de novo desde o Passo 3.

## O robô parou no meio (apareceu "Execução interrompida")

Pode acontecer se a conexão cair, se o SIAFI sair do ar ou se a janela do robô for fechada. **Não refaça a planilha inteira** — parte dela já está no SIAFI.

1. Abra a conferência na pasta **`Conferencia`**. As linhas com `Ok` já foram feitas. As linhas com a coluna **Progresso em branco** ainda não foram.
2. Se houver uma linha marcada **`INTERROMPIDA - VERIFICAR NO SIAFI`**, entre no SIAFI e veja se aquela operação foi registrada:
   - **Foi registrada:** não faça nada, deixe a linha como está.
   - **Não foi registrada:** apague o que está escrito na coluna Progresso dessa linha (deixe a célula vazia) e salve.
3. **Feche o Excel.**
4. Rode o robô de novo, **sem colocar planilha nova** na pasta `Remanejados`. Ele avisa que está **retomando** e faz só as linhas em branco.

> Se você fechou a janela do robô sem querer, o caminho é o mesmo: rode de novo que ele traz a conferência de volta e continua.
>
> Se você colocar uma planilha **nova** antes de terminar a que foi interrompida, o robô processa só a nova, arquiva a antiga e **avisa quantas linhas dela ficaram sem fazer**. Prefira terminar a interrompida primeiro.
>
> O robô só retoma sozinho uma conferência que **ele mesmo** devolveu interrompida nos últimos **7 dias**. Fora disso, ele avisa e não faz nada: confira no SIAFI e coloque as linhas que faltam em uma planilha nova.

## Apareceu "Ja existe uma execucao do robo em andamento"

O robô já está rodando em outra janela. Espere ele terminar. Não abra dois ao mesmo tempo.

## Apareceu "ERRO: o ambiente tem pendencias"

Está faltando alguma coisa da instalação neste computador. Clique duas vezes em **verificar** (`verificar.bat`), tire um print da tela e mande para o suporte técnico da DCMEFO.

## Apareceu "Senha expirada" e abriu um arquivo no Bloco de Notas

Sua senha do SIAFI **venceu**. O robô para, avisa, e **abre sozinho o arquivo `.env`** no Bloco de Notas para você atualizar a senha. Nada foi feito no SIAFI, e as suas planilhas voltaram para a pasta `Remanejados`. Faça assim:

1. Entre no **SIAFI manualmente** (do jeito de sempre) e **troque a sua senha** por uma nova.
2. No arquivo `.env` que abriu, ache a linha que começa com `SENHA=` e troque pela **nova senha**.
3. **Salve** o arquivo (Ctrl + S) e feche o Bloco de Notas.
4. Rode o **robo.bat** de novo (PARTE 1).

## Apareceu "Não foi possível fazer login no SIAFI após várias tentativas"

O robô chegou ao SIAFI, mas não conseguiu entrar. Nada foi feito, e as suas planilhas voltaram para a pasta `Remanejados`. Confira:
- O `USUARIO` e a `SENHA` no arquivo `.env` estão corretos?
- Você consegue entrar no SIAFI manualmente com esse usuário e essa senha?

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
