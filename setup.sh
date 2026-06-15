#!/usr/bin/env bash
# shellcheck shell=bash
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

echo ""
echo "=== Configurando ambiente Ubuntu para o robô SIAFI (Descentralização) ==="
echo ""

# -------------------------------------------------------------------
# 1. Dependências do sistema
# -------------------------------------------------------------------
echo "[1/5] Instalando dependências do sistema..."
sudo apt-get update -q
sudo apt-get install -y --no-install-recommends \
    s3270 x3270 \
    python3 python3-venv python3-pip \
    git

# -------------------------------------------------------------------
# 2. Clone do repositório (filesystem Linux — melhor performance que /mnt/c/)
# -------------------------------------------------------------------
echo ""
echo "[2/5] Clonando repositório..."
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
# 3. Ambiente virtual Python + dependências
# -------------------------------------------------------------------
echo ""
echo "[3/5] Configurando ambiente virtual Python..."
cd "$REPO_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --quiet -r requirements.txt
echo "Dependências Python instaladas."

# -------------------------------------------------------------------
# 4. Aviso WSLg (necessário para visible=True no x3270)
# -------------------------------------------------------------------
echo ""
echo "[4/5] Verificando suporte a interface gráfica (WSLg)..."
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    echo ""
    echo "AVISO: WSLg não detectado nesta sessão."
    echo "O descentralizacao.py usa Emulator(visible=True), que abre a janela gráfica do x3270."
    echo "Se o robô falhar ao abrir a janela, altere visible=True para visible=False"
    echo "em siafi_automacao/descentralizacao.py para rodar sem interface gráfica."
    echo ""
else
    echo "WSLg disponível (DISPLAY=$DISPLAY)."
fi

# -------------------------------------------------------------------
# 5. Variáveis de ambiente (.env)
# -------------------------------------------------------------------
echo ""
echo "[5/5] Configurando variáveis de ambiente..."

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
    read -rp  "  UNIDADE_EXECUTORA (ex: 1451): " UNIDADE_EXECUTORA
    printf 'USUARIO=%s\nSENHA=%s\nUNIDADE_EXECUTORA=%s\n' \
        "$USUARIO" "$SENHA" "$UNIDADE_EXECUTORA" >> .env
    echo "Credenciais SIAFI salvas."
else
    echo ".env já contém as credenciais — mantendo variáveis existentes."
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

    printf 'PASTA_WINDOWS=%s\n' "$PROJETO_BASE" >> .env
    echo "PASTA_WINDOWS salvo."
fi

# Pasta de trabalho local (Linux) — padrão: a pasta data/ deste repositório
if ! grep -q "^PASTA_LINUX=" .env 2>/dev/null; then
    printf 'PASTA_LINUX=%s\n' "$REPO_DIR/data" >> .env
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
echo "  Configuração concluída! O robô será iniciado em seguida."
echo "============================================================"
echo ""
