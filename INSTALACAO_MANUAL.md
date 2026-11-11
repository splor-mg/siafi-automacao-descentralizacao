# Manual de Instalação Manual — Robô SIAFI (Descentralização de Cota)

Passo a passo para instalar o robô **à mão**, sem usar `instalar.bat` / `instalar.ps1` / `setup.sh`, em máquina Windows da rede de governo (CAMG/PRODEMGE), com proxy autenticado.

O uso do dia a dia continua sendo só o **`robo.bat`**. Você nunca precisa rodar `instalar.bat`.

---

## Antes de começar — 3 coisas importantes

**1. Reinício do Windows é obrigatório, não opcional.**
Sempre que um comando abaixo disser "reinicie" — ou o Windows avisar "é necessário reiniciar" — reinicie **antes** de continuar, mesmo que o comando pareça ter funcionado. Pular esse passo é a causa mais comum do WSL ficar "meio instalado" e dar erro estranho depois. Cada ponto do manual onde isso pode acontecer está marcado com 🔁.

**2. O `robo.bat` não exige mais ter rodado o instalador.**
Hoje o `robo.ps1` não verifica "se o instalador rodou" — a cada execução ele confere as **condições reais** (repositório existe, `venv` existe, `.env` preenchido, pastas existem etc.), chamando o `verificar.sh` por baixo dos panos. Ou seja: instale tudo do seu jeito, à mão, seguindo este manual — o robô só recusa rodar se algo *realmente* estiver faltando, não porque você não rodou o `instalar.bat`.

**3. Preste atenção em ONDE cada comando é colado.**
Este manual alterna entre três lugares diferentes: PowerShell do Windows (às vezes como Administrador, às vezes não) e o terminal do Ubuntu (dentro do WSL). Todo bloco de comando abaixo vem com uma etiqueta dizendo onde colar. Colar o comando certo no lugar errado é a segunda causa mais comum de erro neste tipo de instalação.

| Etiqueta | O que é | Como abrir |
|---|---|---|
| 🟦 **PowerShell (Administrador)** | terminal do Windows, com privilégios de administrador | menu Iniciar → botão direito → "Terminal (Admin)" (ou procure "PowerShell", botão direito → "Executar como administrador") |
| 🟦 **PowerShell (comum)** | terminal do Windows, sem privilégios especiais | menu Iniciar → digite "PowerShell" → Enter |
| 🟩 **Ubuntu (bash)** | terminal dentro do WSL/Ubuntu — **não é o PowerShell** | menu Iniciar → app "Ubuntu" (ou "Ubuntu-24.04") |
| 🗂️ **Explorador de Arquivos** | o Windows Explorer, não é um terminal | Win+E, ou clique na barra de endereço |

---

## Resumo rápido — o que precisa existir para o `robo.bat` funcionar

Use esta tabela como checklist final, ou a qualquer momento em que quiser saber "o que falta". O comando oficial para conferir tudo isso automaticamente é o **`verificar.bat`** (passo 10) — ele não altera nada, só avisa.

| Precisa existir | Detalhe |
|---|---|
| Repositório clonado em `~/code/splor-mg/siafi-automacao-descentralizacao` | caminho fixo, não pode ser outro (passo 5) |
| `s3270` e `x3270` instalados | os dois são obrigatórios (passo 4) |
| `venv/` criado com as dependências do `requirements.txt` | `py3270`, `pandas`, `openpyxl`, `python-dotenv` (passo 6) |
| `.env` na raiz do repositório, com `chmod 600` | 5 chaves obrigatórias: `USUARIO`, `SENHA`, `UNIDADE_EXECUTORA`, `UNIDADE_ORCAMENTARIA`, `PASTA_WINDOWS` (passo 7) |
| `PASTA_WINDOWS` apontando para uma pasta que existe de verdade | se for OneDrive, precisa estar sincronizada localmente (passo 8) |
| As 4 subpastas dentro dela, com os nomes exatos | `Remanejados (Insira seu arquivo aqui)`, `Conferencia`, `Realizados/Remanejamento Realizados`, `Realizados/Conferencia Realizados` (passo 8) |
| Proxy configurado em apt, git e pip (rede CAMG/PRODEMGE) | senão nada acima consegue ser baixado/atualizado (passo 3) |

---

## Como o robô funciona

O robô é híbrido: **metade Windows, metade Ubuntu (WSL)**.

```
Windows                                  Ubuntu (WSL2)
────────────────────────────────         ─────────────────────────────────────
robo.bat                                 ~/code/splor-mg/siafi-automacao-descentralizacao
   └─ robo.ps1  ── wsl -d Ubuntu ──►        ├─ git pull (precisa de proxy)
                                            ├─ venv/bin/python consolida.py
                                            └─ venv/bin/python siafi_automacao/descentralizacao.py
                                                  └─ x3270 ──► bhmvsb.prodemge.gov.br (SIAFI, TN3270)

Pasta "Projeto de Descentralização" (OneDrive/Windows) ── acessada pelo Ubuntu via /mnt/c/...
```

Duas coisas fixas no código, que **não podem** mudar:

- O caminho do repositório no Ubuntu: `~/code/splor-mg/siafi-automacao-descentralizacao`.
- Os nomes das 4 subpastas do projeto (passo 8), exatamente como estão escritos, com acentos e parênteses.

---

## 1. Pré-requisitos no Windows

- Windows 10 (build 19041+) ou Windows 11.
- Virtualização habilitada na BIOS (Gerenciador de Tarefas → Desempenho → CPU → "Virtualização: Habilitada").
- Permissão de administrador local (só para instalar o WSL).
- Estar na rede da SEPLAG ou com VPN ligada — o SIAFI só responde de dentro da rede.

---

## 2. Instalar o WSL + Ubuntu

Abra o **PowerShell como Administrador** (botão direito no menu Iniciar → "Terminal (Admin)").

### 2.1. Caminho normal (se a máquina alcança a Microsoft Store)

🟦 **PowerShell (Administrador)**
```powershell
wsl --install -d Ubuntu-24.04
```

🔁 **Reinicie o computador quando ele pedir.** Não continue sem reiniciar.

> Deu **"O tempo limite da operação foi atingido"** sem nenhuma outra mensagem? Esse é o sintoma típico de bloqueio de proxy — não precisa tentar adivinhar, vá direto para o passo 2.2.

### 2.2. Se o download falhar por causa do proxy

Em muitas máquinas da rede o `wsl --install` falha porque o download não passa pelo proxy autenticado. Nesse caso, baixe os pacotes com o `curl.exe` (que aceita usuário/senha de proxy) e instale manualmente:

🟦 **PowerShell (Administrador)**
```powershell
# 0) Checar se o wsl.exe já é o motor completo ou só o "stub" do Windows
wsl --status
```
> Se der erro de argumento desconhecido, ou só mostrar uma lista de uso resumida (sem linhas de versão), o `wsl.exe` desta máquina é só o stub — o motor real do WSL nunca foi instalado. Rode primeiro:
> ```powershell
> wsl --install --inbox --no-distribution
> ```
> Esse comando instala Virtual Machine Platform, o Subsistema do Windows para Linux e o kernel via DISM/Windows Update — **não** passa pelo mesmo caminho de download que trava com o proxy. Depois de rodar, 🔁 **reinicie o computador** antes de continuar.

🟦 **PowerShell (Administrador)**
```powershell
# 1) Habilitar os componentes do Windows (caso o passo 0 acima não tenha sido suficiente)
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

🔁 **Reinicie o computador agora, antes de continuar.** Os dois comandos acima só têm efeito depois do reinício — rodar o próximo passo sem reiniciar dá erro.

🟦 **PowerShell (Administrador)** — abra de novo depois de reiniciar
```powershell
wsl --version
```
> Confirme que agora aparece a versão completa (WSL, kernel, WSLg etc.), não mais o help resumido. Só continue quando isso estiver certo.

> ⚠️ **Antes de abrir esta janela elevada, confira que ela vai autenticar com a mesma conta Windows da sua sessão normal.** Em algumas redes de domínio (como a PRODEMGE), "Executar como Administrador" pede uma credencial de **outra conta admin** — nesse caso qualquer arquivo salvo em `$env:TEMP` fica no perfil dessa outra conta e "some" quando você volta para o PowerShell comum. Rode `whoami` nas duas janelas e compare; se forem contas diferentes, use uma pasta fixa em vez de `$env:TEMP`, por exemplo `C:\Temp\wsl-install\` (criada com `mkdir -Force`), assim os dois contextos enxergam o mesmo arquivo.

🟦 **PowerShell (Administrador)**
```powershell
# 2) Baixar o instalador do WSL (.msi) e a distro Ubuntu através do proxy
$proxy = "http://proxycamg.prodemge.gov.br:8080"
$cred  = "SEU_LOGIN:SUA_SENHA"     # aqui NÃO precisa codificar caracteres especiais
$dest  = "C:\Temp\wsl-install"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

# Confira a versão mais recente em https://github.com/microsoft/WSL/releases antes de rodar —
# o nome do arquivo muda a cada release e um link "latest" fixo (ex: Microsoft.WSL.msixbundle)
# costuma dar 404.
curl.exe -L -k --fail -x $proxy --proxy-user $cred `
  -o "$dest\wsl.msi" `
  "https://github.com/microsoft/WSL/releases/download/2.7.3/wsl.2.7.3.0.x64.msi"

curl.exe -L --fail -x $proxy --proxy-user $cred `
  -o "$dest\ubuntu.appxbundle" `
  "https://wslstorestorage.blob.core.windows.net/wslblob/Ubuntu2404-240425.AppxBundle"

# 3) Instalar — o .msi é mais robusto que o .msixbundle: não depende de Add-AppxPackage
#    nem da dependência VCLibs, e instala como um programa comum.
Start-Process msiexec.exe -ArgumentList "/i `"$dest\wsl.msi`" /quiet /norestart" -Wait
wsl --version    # confirme que retorna a versão completa antes de seguir

# O Ubuntu, por outro lado, é um pacote UWP e precisa mesmo do Add-AppxPackage.
# Pode ser rodado numa janela SEM privilégios de administrador.
Add-AppxPackage -Path "$dest\ubuntu.appxbundle"
wsl --set-default-version 2
```

> Se o proxy bloquear o domínio `blob.core.windows.net`, troque a URL do Ubuntu por `https://aka.ms/wslubuntu`.
> O `-k` ignora o certificado — necessário porque o proxy da PRODEMGE intercepta o SSL (use-o só na chamada do `.msi`; o `.appxbundle` não teve esse problema em teste, mas se travar, adicione `-k` também nessa segunda chamada).

### 2.3. Criar o usuário do Ubuntu

Abra o **Ubuntu** pelo menu Iniciar. Na primeira vez ele pede:

- **Username:** minúsculo, sem espaço e sem acento (ex.: `joao.silva`)
- **Password:** senha **local do Ubuntu** (não é a do SIAFI nem a da rede) — anote, ela será pedida em todo `sudo`

Confirme que ficou tudo certo:

🟦 **PowerShell (comum, não precisa ser Administrador)**
```powershell
wsl --list --verbose      # deve mostrar Ubuntu-24.04 ... Running/Stopped ... 2
```

> **Se `wsl --list` continuar vazio mesmo após o `Add-AppxPackage` "concluir" sem erro:** o pacote registrou, mas o WSL só cria a instância no primeiro lançamento manual do app — e o nome do executável nem sempre aparece de imediato no PATH (`ubuntu2404.exe` pode dar "não reconhecido"). Force o primeiro lançamento assim:
> ```powershell
> $pkg = Get-AppxPackage *Ubuntu*
> $aumid = (Get-AppxPackageManifest $pkg).Package.Applications.Application.Id
> explorer.exe "shell:AppsFolder\$($pkg.PackageFamilyName)!$aumid"
> ```
> Isso abre a janela do Ubuntu como se tivesse clicado no ícone do menu Iniciar, disparando a configuração inicial de usuário/senha.

---

## 3. Configurar o proxy dentro do Ubuntu

> A partir daqui até o passo 8, **todo comando é dentro do terminal Ubuntu (🟩)** — abra o app "Ubuntu" pelo menu Iniciar, não o PowerShell.

**Configure o proxy por ferramenta (apt, git, pip), não só em variáveis de ambiente.** Três motivos concretos:

- O `sudo` limpa o ambiente — `export http_proxy` no shell **não chega no `sudo apt`**.
- O `robo.ps1` roda o `git pull` de forma não-interativa, que **não lê o `~/.bashrc`**. Se o proxy do git estiver só ali, todo dia o robô vai avisar *"Nao foi possivel atualizar (git pull)"* e rodar com a versão desatualizada (isso não trava a execução, só deixa o robô desatualizado).
- O pip funciona com variável de ambiente, mas o `pip.conf` garante o mesmo comportamento sempre.

As variáveis de ambiente no `.bashrc` continuam valendo como complemento, para `curl`, `wget` e uso interativo.

> **A senha fica em texto puro nesses arquivos** — é inevitável em proxy autenticado. Por isso todos levam `chmod 600` (só o dono lê). Quando a senha da rede mudar, atualize os quatro lugares.

### 3.1. Codificar a senha (percent-encoding)

Na URL do proxy, `@`, `#`, `:`, `/`, `%` quebram o endereço e precisam virar código. Gere a versão codificada:

🟩 **Ubuntu (bash)**
```bash
python3 -c "import urllib.parse,getpass; print(urllib.parse.quote(getpass.getpass('Senha: '), safe=''))"
```

Use o resultado no lugar de `SENHA_CODIFICADA` daqui em diante. O login é a matrícula/usuário da rede.

### 3.2. apt (pacotes do sistema)

🟩 **Ubuntu (bash)**
```bash
sudo tee /etc/apt/apt.conf.d/95proxy >/dev/null <<'EOF'
Acquire::http::Proxy  "http://LOGIN:SENHA_CODIFICADA@proxycamg.prodemge.gov.br:8080";
Acquire::https::Proxy "http://LOGIN:SENHA_CODIFICADA@proxycamg.prodemge.gov.br:8080";
EOF
sudo chmod 600 /etc/apt/apt.conf.d/95proxy
```

### 3.3. git (usado pelo clone e pelo `git pull` de toda execução)

🟩 **Ubuntu (bash)**
```bash
git config --global http.proxy  "http://LOGIN:SENHA_CODIFICADA@proxycamg.prodemge.gov.br:8080"
git config --global https.proxy "http://LOGIN:SENHA_CODIFICADA@proxycamg.prodemge.gov.br:8080"
git config --global http.sslVerify false     # o proxy intercepta o SSL
chmod 600 ~/.gitconfig
```

### 3.4. pip (dependências Python)

🟩 **Ubuntu (bash)**
```bash
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf <<'EOF'
[global]
proxy = http://LOGIN:SENHA_CODIFICADA@proxycamg.prodemge.gov.br:8080
trusted-host =
    pypi.org
    files.pythonhosted.org
    pypi.python.org
EOF
chmod 600 ~/.config/pip/pip.conf
```

### 3.5. Variáveis de ambiente (curl, wget, uso interativo)

🟩 **Ubuntu (bash)**
```bash
cat > ~/.proxyrc <<'EOF'
export http_proxy="http://LOGIN:SENHA_CODIFICADA@proxycamg.prodemge.gov.br:8080"
export https_proxy="$http_proxy"
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$http_proxy"
export no_proxy="localhost,127.0.0.1,.prodemge.gov.br,.mg.gov.br"
export NO_PROXY="$no_proxy"
EOF
chmod 600 ~/.proxyrc
echo '[ -f ~/.proxyrc ] && . ~/.proxyrc' >> ~/.bashrc
source ~/.proxyrc
```

> O `no_proxy` com `.prodemge.gov.br` é importante: o SIAFI (`bhmvsb.prodemge.gov.br`) é acesso interno e não deve passar pelo proxy.

### 3.6. Testar antes de seguir

🟩 **Ubuntu (bash)**
```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://pypi.org      # espera 200
git ls-remote https://github.com/splor-mg/siafi-automacao-descentralizacao.git >/dev/null && echo "git OK"
```

Deu **407 Proxy Authentication Required**? Login ou senha codificada errados — refaça o passo 3.1.

> ⚠️ Várias tentativas com senha errada podem **bloquear seu usuário de rede**. Errou duas vezes? Confirme a senha antes de tentar de novo.

### 3.7. Opção avançada (se a senha muda com frequência)

Instalar o **CNTLM** (`sudo apt install cntlm`): guarda um hash da senha em um único arquivo e expõe um proxy sem autenticação em `127.0.0.1:3128`. Todos os arquivos acima passam a apontar para lá — sem senha em lugar nenhum. Vale a pena só se o robô rodar em várias máquinas.

---

## 4. Instalar as dependências do sistema

🟩 **Ubuntu (bash)**
```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    s3270 x3270 python3 python3-venv python3-pip git
```

`s3270`/`x3270` são o emulador de terminal TN3270 que fala com o SIAFI — **os dois são obrigatórios**. `python3-venv` é necessário para o `python3 -m venv` funcionar.

---

## 5. Clonar o repositório (caminho fixo!)

O caminho é fixo no `robo.ps1`. Não use outro diretório.

🟩 **Ubuntu (bash)**
```bash
mkdir -p ~/code/splor-mg
cd ~/code/splor-mg
git clone https://github.com/splor-mg/siafi-automacao-descentralizacao.git
cd siafi-automacao-descentralizacao
```

> Deu **"destination path already exists and is not an empty directory"**? É resquício de uma tentativa anterior — não precisa apagar nada, só entre na pasta com `cd siafi-automacao-descentralizacao` e siga o manual normalmente a partir daí.

Repositório privado? O git pede usuário e senha — use seu usuário do GitHub e um **Personal Access Token (PAT)** no lugar da senha. Para não digitar toda vez:

🟩 **Ubuntu (bash)**
```bash
git config --global credential.helper store
chmod 600 ~/.git-credentials 2>/dev/null
```

Confirme o caminho:

🟩 **Ubuntu (bash)**
```bash
pwd    # precisa imprimir: /home/SEU_USUARIO/code/splor-mg/siafi-automacao-descentralizacao
```

Se o clone falhar com erro de proxy, revise o passo 3.3 (git precisa do proxy configurado *antes* de clonar).

---

## 6. Criar o ambiente virtual Python

> Confirme antes que o passo 4 realmente instalou `python3-venv` e `python3-pip` (às vezes essa etapa é pulada sem querer). Se aparecer o erro abaixo, é exatamente isso:
> ```
> The virtual environment was not created successfully because ensurepip is not available.
> ```
> Resolva com:
> ```bash
> sudo apt install -y python3.12-venv python3-pip
> rm -rf venv     # apaga a tentativa incompleta antes de recriar
> ```

🟩 **Ubuntu (bash)**
```bash
cd ~/code/splor-mg/siafi-automacao-descentralizacao
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Se você não criou o `pip.conf` do passo 3.4, passe o proxy na mão:

🟩 **Ubuntu (bash)**
```bash
pip install --proxy "http://LOGIN:SENHA_CODIFICADA@proxycamg.prodemge.gov.br:8080" \
    --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    -r requirements.txt
```

Conferir:

🟩 **Ubuntu (bash)**
```bash
python -c "import py3270, pandas, openpyxl, dotenv; print('deps OK')"
```

---

## 7. Criar o arquivo `.env`

Fica na raiz do repositório e nunca vai para o git.

🟩 **Ubuntu (bash)**
```bash
cd ~/code/splor-mg/siafi-automacao-descentralizacao
cp .env.example .env
chmod 600 .env
nano .env      # edite e salve com Ctrl+O, Enter, Ctrl+X
```

> **Prefere não usar o `nano`?** Dá para criar o arquivo direto via heredoc, sem abrir editor nenhum — só trocar os valores de exemplo pelos seus:
> ```bash
> cat > .env <<'EOF'
> USUARIO=1234567
> SENHA=sua_senha_do_siafi
> UNIDADE_EXECUTORA=1500008
> UNIDADE_ORCAMENTARIA=1501
> PASTA_WINDOWS=/mnt/c/Users/SEU_USUARIO_WINDOWS/OneDrive - CAMG/General/@dcmefo/2026/Projeto de Descentralização
> PASTA_LINUX=/home/SEU_USUARIO_LINUX/code/splor-mg/siafi-automacao-descentralizacao/data
> EOF
> chmod 600 .env
> ```

Conteúdo final (digite dentro do editor `nano` que abriu — sem aspas, sem espaço em volta do `=`):

```ini
USUARIO=1234567
SENHA=sua_senha_do_siafi
UNIDADE_EXECUTORA=1500008
UNIDADE_ORCAMENTARIA=1501
PASTA_WINDOWS=/mnt/c/Users/SEU_USUARIO_WINDOWS/OneDrive - CAMG/General/@dcmefo/2026/Projeto de Descentralização
PASTA_LINUX=/home/SEU_USUARIO_LINUX/code/splor-mg/siafi-automacao-descentralizacao/data
```

| Chave | O que é | Obrigatória |
|---|---|---|
| `USUARIO` | login do SIAFI (normalmente o MASP com dígito verificador) | sim |
| `SENHA` | senha do SIAFI (não é a da rede/proxy) | sim |
| `UNIDADE_EXECUTORA` | 7 dígitos | sim |
| `UNIDADE_ORCAMENTARIA` | 4 dígitos | sim |
| `PASTA_WINDOWS` | pasta-raiz `Projeto de Descentralização`, em formato WSL (`/mnt/c/...`) | sim |
| `PASTA_LINUX` | pasta de trabalho local; se faltar, usa `<repo>/data` | opcional |
| `SIAFI_VISIVEL` | `false` roda sem abrir a janela do SIAFI (para quando não há WSLg); padrão `true` | opcional |

> `USUARIO` e `SENHA` têm no máximo 8 caracteres cada: é o tamanho do campo na tela do SIAFI. Se um deles passar disso, o robô avisa e não tenta o login.

> O sistema de acesso (`simg`) é fixo no código e não vai no `.env`.

Para achar o `PASTA_WINDOWS` sem errar: abra a pasta no 🗂️ **Explorador de Arquivos**, copie o caminho da barra de endereço e converta:

🟩 **Ubuntu (bash)**
```bash
wslpath -u 'C:\Users\SEU_USUARIO\OneDrive - CAMG\General\@dcmefo\2026\Projeto de Descentralização'
```

---

## 8. Criar as pastas

### 8.1. Estrutura do projeto (lado Windows/OneDrive)

Os nomes precisam ser **exatamente** estes — com acento, espaço e parênteses:

🟩 **Ubuntu (bash)**
```bash
BASE="/mnt/c/Users/SEU_USUARIO_WINDOWS/OneDrive - CAMG/General/@dcmefo/2026/Projeto de Descentralização"

mkdir -p "$BASE/Remanejados (Insira seu arquivo aqui)" \
         "$BASE/Conferencia" \
         "$BASE/Realizados/Remanejamento Realizados" \
         "$BASE/Realizados/Conferencia Realizados"
```

Resultado esperado:

```
Projeto de Descentralização/
├── Remanejados (Insira seu arquivo aqui)/   ← você coloca as planilhas aqui
├── Conferencia/                             ← o robô devolve o consolidado aqui
└── Realizados/
    ├── Remanejamento Realizados/            ← entradas já processadas
    └── Conferencia Realizados/              ← conferências de dias anteriores
```

### 8.2. Pasta de trabalho local (lado Linux)

🟩 **Ubuntu (bash)**
```bash
mkdir -p ~/code/splor-mg/siafi-automacao-descentralizacao/data
```

> Se a pasta do projeto estiver no OneDrive, garanta que está **sincronizada/baixada localmente** ("Sempre manter neste dispositivo"). Arquivos só na nuvem não aparecem para o WSL.

---

## 9. Deixar o `robo.bat` acessível no Windows

O `robo.bat` roda no Windows e chama o `robo.ps1` que está na mesma pasta dele. Duas opções:

**Opção A (recomendada) — atalho direto do repositório.**

🗂️ **Explorador de Arquivos** — cole na barra de endereço:
```
\\wsl.localhost\Ubuntu-24.04\home\SEU_USUARIO_LINUX\code\splor-mg\siafi-automacao-descentralizacao
```

Clique direito em `robo.bat` → **Enviar para → Área de trabalho (criar atalho)**. Assim o `robo.ps1` está sempre na versão do `git pull`.

**Opção B — copiar para uma pasta do Windows.** Copie `robo.bat`, `robo.ps1`, `verificar.bat` e `verificar.ps1` para, por exemplo, `C:\Robo SIAFI\`. O `robo.ps1` se auto-atualiza a partir do repositório a cada execução, então a cópia não fica velha.

> Não use atalho para o `.ps1` direto: quem precisa ser clicado é o `.bat`.

---

## 10. Verificar a instalação

Antes de rodar o robô de verdade:

🟩 **Ubuntu (bash)**
```bash
cd ~/code/splor-mg/siafi-automacao-descentralizacao
bash verificar.sh
```

Ou, mais fácil: 🗂️ **Explorador de Arquivos** — clique duas vezes em **`verificar.bat`** (não é comando de terminal, é um duplo clique no arquivo).

Ele confere repositório, arquivos, venv, dependências, `s3270`/`x3270`, todas as chaves do `.env` e as pastas — a mesma checagem que o `robo.bat` faz sozinho antes de rodar. **Só siga adiante quando não houver nenhum `[FALHA]`.** Avisos (`[AVISO]`) não impedem a execução.

---

## 11. Executar o robô

1. Confirme que está na rede da SEPLAG (ou com VPN ligada).
2. Coloque as planilhas (com a aba `Execucao`) em `Remanejados (Insira seu arquivo aqui)` e feche os arquivos no Excel.
3. 🗂️ **Explorador de Arquivos** — clique duas vezes em **`robo.bat`** (não precisa abrir terminal nenhum; o `.bat` abre tudo sozinho).

Ordem de execução: verifica o ambiente → `git pull` (se falhar por proxy, só avisa e segue com a versão local) → `consolida.py` → `descentralizacao.py`.

Códigos de saída do `robo.bat`:

| Código | Significado | O que fazer |
|---|---|---|
| `0` | foi até o fim, ou não havia planilha nova nem linha pendente | conferir a coluna `Progresso` do arquivo em `Conferencia` |
| `3` | senha do SIAFI expirada; nada foi enviado e as planilhas voltaram para `Remanejados` | trocar a senha no SIAFI, atualizar `SENHA` no `.env` (o robô abre o arquivo sozinho) e rodar de novo |
| `10` | já existe outra execução do robô em andamento | esperar terminar |
| `1` / outros | pendência de ambiente, erro de preenchimento nas planilhas, falha de conexão/login ou execução interrompida | ler as mensagens da janela — elas dizem o que foi feito e o que fazer; para pendência de ambiente, rodar o `verificar.bat` |

Se a execução for interrompida no meio, a conferência volta para a pasta `Conferencia` com o que já foi feito, e rodar de novo **sem planilha nova** retoma as linhas em branco. O passo a passo para quem usa está no RUNBOOK ("O robô parou no meio").

O uso do dia a dia está detalhado no **[RUNBOOK.md](RUNBOOK.md)**.

---

## 12. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `407 Proxy Authentication Required` | senha não codificada, ou login errado | refaça o passo 3.1 e reaplique 3.2–3.5 |
| `[aviso] Nao foi possivel atualizar (git pull)` toda execução | proxy do git só no `.bashrc` | configure com `git config --global http.proxy` (passo 3.3) — isso **não trava** o robô, só deixa ele desatualizado |
| `SSL certificate problem: self signed certificate in certificate chain` | proxy intercepta o SSL | `git config --global http.sslVerify false` e `--trusted-host` no pip |
| `sudo apt update` falha, mas `curl` funciona | `sudo` descarta as variáveis de ambiente | crie o `/etc/apt/apt.conf.d/95proxy` (passo 3.2) |
| WSL não instala / trava depois do `dism.exe` | computador não foi reiniciado | 🔁 reinicie e tente de novo (veja "Antes de começar") |
| `[FALHA] repositorio nao encontrado` | clonou em outro caminho | mova para `~/code/splor-mg/siafi-automacao-descentralizacao` |
| `[FALHA] PASTA_WINDOWS não acessível` | OneDrive não sincronizado, ou caminho em formato Windows no `.env` | baixe a pasta localmente; use `/mnt/c/...` (`wslpath -u`) |
| `[FALHA] UNIDADE_ORCAMENTARIA ausente` | chave esquecida no `.env` | adicione a linha `UNIDADE_ORCAMENTARIA=` |
| Robô trava ao abrir a tela do x3270 | WSLg indisponível | acrescente a linha `SIAFI_VISIVEL=false` ao `.env` (não altere o código: arquivo modificado localmente faz o `git pull` automático parar de funcionar) |
| `Não foi possível conectar ao SIAFI` | fora da rede/VPN, ou `bhmvsb.prodemge.gov.br` indo pelo proxy | ligue a VPN e confirme `.prodemge.gov.br` no `no_proxy`; as planilhas voltam sozinhas para `Remanejados` |
| Erro de leitura de planilha | arquivo aberto no Excel, sem a aba `Execucao` ou em formato `.xls` | feche o Excel, confira a aba e salve como `.xlsx` |
| `Ja existe uma execucao do robo em andamento` sem nenhum robô aberto | sobrou um processo do robô ou do x3270 de uma execução anterior | feche a janela do SIAFI que tiver ficado aberta; se persistir, rode `wsl --shutdown` no PowerShell e tente de novo |
| `ensurepip is not available` ao criar o `venv` | `python3-venv` não foi instalado (passo 4 pulado ou incompleto) | `sudo apt install python3.12-venv`, depois `rm -rf venv` e recrie |
| `Exec format error` ao rodar `code .` (ou outro `.exe` do Windows) dentro do Ubuntu | interoperabilidade WSL↔Windows não registrada | confira com `cat /proc/sys/fs/binfmt_misc/WSLInterop`; se ausente/desabilitado, adicione `[interop]\nenabled=true` em `/etc/wsl.conf` e rode `wsl --shutdown` **no PowerShell** (não dentro do bash — `exit` primeiro) |
| `wsl` command not found dentro do bash do Ubuntu | comando digitado no terminal errado | `wsl.exe` só existe no lado Windows; dê `exit` para sair do Ubuntu antes de rodar comandos `wsl --...` |

---

Terminou os passos 1–10 e o `verificar.bat` não mostrou nenhum `[FALHA]`? A instalação está completa — use a tabela em **"Resumo rápido"** no topo deste manual para conferir de novo a qualquer momento.
