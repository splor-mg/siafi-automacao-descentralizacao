#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2086
set -euo pipefail

REPO_DIR="$HOME/code/splor-mg/siafi-automacao-descentralizacao"
REPO_URL="https://github.com/splor-mg/siafi-automacao-descentralizacao.git"

# Converte um caminho do Windows (C:\Users\...) para o formato WSL (/mnt/c/...).
# Se já vier em formato WSL (/mnt/...), devolve praticamente como está.
to_wsl_path() {
    local p="$1"
    p="${p//\\//}"                       # barras invertidas -> barras normais
    if [[ "$p" =~ ^([A-Za-z]):/(.*)$ ]]; then
        local drive
        drive=$(printf '%s' "${BASH_REMATCH[1]}" | tr '[:upper:]' '[:lower:]')
        p="/mnt/${drive}/${BASH_REMATCH[2]}"
    fi
    p="${p%/}"                           # remove barra final, se houver
    printf '%s' "$p"
}

# Codifica para URL (percent-encoding) — usado na senha do proxy, que pode
# conter caracteres especiais como '@', ':' etc.
urlencode() {
    local s="$1" out="" c hex i
    for (( i=0; i<${#s}; i++ )); do
        c="${s:$i:1}"
        case "$c" in
            [a-zA-Z0-9.~_-]) out+="$c" ;;
            *) printf -v hex '%%%02X' "'$c"; out+="$hex" ;;
        esac
    done
    printf '%s' "$out"
}

# Acrescenta uma linha ao .env. Antes garante que o arquivo termina em quebra
# de linha: um .env salvo pelo Bloco de Notas do Windows pode não terminar, e a
# chave nova ficaria grudada no fim da última linha, estragando as duas.
anexar_env() {
    if [ -s .env ] && [ -n "$(tail -c1 .env)" ]; then
        printf '\n' >> .env
    fi
    printf '%s\n' "$1" >> .env
}

echo ""
echo "=== Configurando ambiente Ubuntu para o robô SIAFI (Descentralização) ==="
echo ""

# -------------------------------------------------------------------
# 1. Rede: proxy do PRODEMGE (apt, git, pip) + certificado SSL
# -------------------------------------------------------------------
echo "[1/6] Configurando acesso à rede (proxy PRODEMGE)..."

# Flags que serão aplicadas ao pip mais à frente (vazias se não usar proxy).
PIP_PROXY=""
PIP_TRUSTED=""

read -rp "  Está na rede da CAMG/PRODEMGE e precisa de proxy? [S/n]: " _usar_proxy
_usar_proxy="${_usar_proxy:-S}"

if [[ "$_usar_proxy" =~ ^[Ss] ]]; then
    PROXY_HOST="proxycamg.prodemge.gov.br:8080"

    read -rp  "  Usuário do proxy (matrícula): " PXUSER
    read -rsp "  Senha do proxy (não aparece): " PXPASS; echo ""

    PXUSER_ENC=$(urlencode "$PXUSER")
    PXPASS_ENC=$(urlencode "$PXPASS")
    PROXY_URL="http://${PXUSER_ENC}:${PXPASS_ENC}@${PROXY_HOST}"

    # Variáveis de ambiente (valem para git, curl, pip nesta sessão)
    export http_proxy="$PROXY_URL"  https_proxy="$PROXY_URL"
    export HTTP_PROXY="$PROXY_URL"  HTTPS_PROXY="$PROXY_URL"
    export no_proxy="localhost,127.0.0.1"

    # apt via proxy (os pacotes do Ubuntu vêm por HTTP — só precisa do proxy).
    # Arquivo só legível pelo root, pois contém a senha.
    echo "Acquire::http::Proxy \"$PROXY_URL\";
Acquire::https::Proxy \"$PROXY_URL\";" | sudo tee /etc/apt/apt.conf.d/95proxy >/dev/null
    sudo chmod 600 /etc/apt/apt.conf.d/95proxy

    # git: usa o proxy (via env acima) e ignora a validação do certificado,
    # já que o proxy intercepta o SSL. GIT_SSL_NO_VERIFY é temporário (só esta sessão).
    export GIT_SSL_NO_VERIFY=true

    # pip: atravessa o proxy e confia nos hosts do PyPI (o proxy quebra o certificado).
    PIP_PROXY="--proxy $PROXY_URL"
    PIP_TRUSTED="--trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org"

    echo "  Proxy configurado."
else
    echo "  Sem proxy (rede aberta)."
fi
echo ""

# -------------------------------------------------------------------
# 2. Dependências do sistema
# -------------------------------------------------------------------
echo "[2/6] Instalando dependências do sistema..."
sudo apt-get update -q
sudo apt-get install -y --no-install-recommends \
    s3270 x3270 \
    python3 python3-venv python3-pip \
    git

# -------------------------------------------------------------------
# 3. Clone do repositório (filesystem Linux — melhor performance que /mnt/c/)
# -------------------------------------------------------------------
echo ""
echo "[3/6] Clonando repositório..."
if [ ! -d "$REPO_DIR/.git" ]; then
    mkdir -p "$HOME/code/splor-mg"

    if git clone "$REPO_URL" "$REPO_DIR" 2>/dev/null; then
        echo "Clone concluído."
    else
        echo ""
        echo "Repositório privado ou sem acesso. Informe seu GitHub Personal Access Token:"
        echo "(O token não aparecerá na tela)"
        read -rs GH_TOKEN
        echo ""
        git -c "url.https://${GH_TOKEN}@github.com/.insteadOf=https://github.com/" \
            clone "$REPO_URL" "$REPO_DIR"
        echo "Clone concluído."
    fi
else
    echo "Repositório já existe em $REPO_DIR, pulando clone."
fi

# -------------------------------------------------------------------
# 4. Ambiente virtual Python + dependências
# -------------------------------------------------------------------
echo ""
echo "[4/6] Configurando ambiente virtual Python..."
cd "$REPO_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --quiet ${PIP_PROXY} ${PIP_TRUSTED} -r requirements.txt
echo "Dependências Python instaladas."

# -------------------------------------------------------------------
# 5. Aviso WSLg (necessário para a janela do x3270; ver SIAFI_VISIVEL)
# -------------------------------------------------------------------
echo ""
echo "[5/6] Verificando suporte a interface gráfica (WSLg)..."
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    echo ""
    echo "AVISO: WSLg não detectado nesta sessão."
    echo "Por padrão o robô abre a janela gráfica do x3270 para você acompanhar."
    echo "Se ele falhar ao abrir a janela, acrescente a linha SIAFI_VISIVEL=false"
    echo "ao arquivo .env para rodar sem interface gráfica."
    echo ""
else
    echo "WSLg disponível (DISPLAY=$DISPLAY)."
fi

# -------------------------------------------------------------------
# 6. Variáveis de ambiente (.env)
# -------------------------------------------------------------------
echo ""
echo "[6/6] Configurando variáveis de ambiente..."

# Garantir que .env existe com permissões restritas
if [ ! -f ".env" ]; then
    touch .env
    chmod 600 .env
fi

# Coletar apenas as credenciais ausentes (o sistema é fixo: 'simg')
if ! grep -q "^USUARIO=" .env 2>/dev/null; then
    echo ""
    echo "Informe as credenciais de acesso ao SIAFI:"
    echo ""
    read -rp  "  USUARIO: "                      USUARIO
    read -rsp "  SENHA (não aparece na tela): "  SENHA
    echo ""
    read -rp  "  UNIDADE_EXECUTORA, 7 dígitos (ex: 1500008): " UNIDADE_EXECUTORA
    anexar_env "USUARIO=$USUARIO"
    anexar_env "SENHA=$SENHA"
    anexar_env "UNIDADE_EXECUTORA=$UNIDADE_EXECUTORA"
    echo "Credenciais SIAFI salvas."
else
    echo ".env já contém as credenciais — mantendo variáveis existentes."
fi

# UO da unidade executora: o robô a digita em toda descentralização. Perguntada
# à parte para que uma instalação antiga, feita antes de esta chave existir,
# seja completada sem pedir de novo o que já está no .env.
if ! grep -q "^UNIDADE_ORCAMENTARIA=" .env 2>/dev/null; then
    echo ""
    UNIDADE_ORCAMENTARIA=""
    while [ -z "$UNIDADE_ORCAMENTARIA" ]; do
        read -rp "  UNIDADE_ORCAMENTARIA da sua unidade executora, 4 dígitos (ex: 1501): " UNIDADE_ORCAMENTARIA
    done
    anexar_env "UNIDADE_ORCAMENTARIA=$UNIDADE_ORCAMENTARIA"
    echo "UNIDADE_ORCAMENTARIA salva."
fi

# Pasta-raiz "Projeto de Descentralização" — pergunta o caminho-pai, cria a
# estrutura de pastas e salva PASTA_WINDOWS no .env.
if ! grep -q "^PASTA_WINDOWS=" .env 2>/dev/null; then
    # Detectar usuário Windows para sugerir o caminho-pai padrão
    _win_user=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r\n' || true)
    _year=$(date +%Y)
    if [ -n "$_win_user" ]; then
        _base_sugestao="C:\\Users\\${_win_user}\\OneDrive - CAMG\\General\\@dcmefo\\${_year}"
    else
        _base_sugestao=""
    fi

    echo ""
    echo "Qual o caminho que irá ser utilizado no projeto?"
    echo "(informe a pasta ONDE a 'Projeto de Descentralização' será criada —"
    echo " pode colar o caminho do Windows, ex.:"
    echo " C:\\Users\\SEU_USUARIO\\OneDrive - CAMG\\General\\@dcmefo\\${_year})"
    if [ -n "$_base_sugestao" ]; then
        echo "  Sugestão detectada: $_base_sugestao"
        read -rp "  Caminho [Enter para aceitar]: " _base_in
        _base_in="${_base_in:-$_base_sugestao}"
    else
        read -rp "  Caminho: " _base_in
    fi

    _base_wsl=$(to_wsl_path "$_base_in")

    # Se o usuário já incluiu "Projeto de Descentralização" no fim, não duplica
    if [[ "$_base_wsl" == *"Projeto de Descentralização" ]]; then
        PROJETO_BASE="$_base_wsl"
    else
        PROJETO_BASE="$_base_wsl/Projeto de Descentralização"
    fi

    echo ""
    echo "Criando a estrutura de pastas em:"
    echo "  $PROJETO_BASE"
    mkdir -p \
        "$PROJETO_BASE/Remanejados (Insira seu arquivo aqui)" \
        "$PROJETO_BASE/Conferencia" \
        "$PROJETO_BASE/Realizados/Remanejamento Realizados" \
        "$PROJETO_BASE/Realizados/Conferencia Realizados"
    echo "Pastas criadas (ou já existentes)."

    anexar_env "PASTA_WINDOWS=$PROJETO_BASE"
    echo "PASTA_WINDOWS salvo."
fi

# Pasta de trabalho local (Linux) — padrão: a pasta data/ deste repositório
if ! grep -q "^PASTA_LINUX=" .env 2>/dev/null; then
    anexar_env "PASTA_LINUX=$REPO_DIR/data"
    echo "PASTA_LINUX definido como $REPO_DIR/data."
fi

# -------------------------------------------------------------------
# Sentinela
# -------------------------------------------------------------------
echo ""
echo "Marcando setup como concluído..."
touch "$REPO_DIR/.setup_done"

echo ""
echo "============================================================"
echo "  Configuração concluída! Para usar, execute o robo.bat."
echo "============================================================"
echo ""