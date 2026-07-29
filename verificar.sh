#!/usr/bin/env bash
# ============================================================================
# verificar.sh — Diagnóstico de pré-requisitos do Robô SIAFI (Descentralização)
#
# Checa as CONDIÇÕES REAIS de funcionamento (repositório, venv, dependências,
# binários do 3270, variáveis do .env e caminhos configurados), em vez de
# confiar em um arquivo-marcador (.setup_done).
#
# Uso:
#   bash verificar.sh            # diagnóstico completo (verboso)
#   bash verificar.sh --quiet    # só mostra pendências (usado pelo robo.ps1)
#
# Saída:
#   0  -> ambiente pronto (o robô pode rodar)
#   1  -> há pendências [FALHA] a resolver
#
# Não altera nada: apenas inspeciona.
# ============================================================================

set -uo pipefail

REPO_DIR="$HOME/code/splor-mg/siafi-automacao-descentralizacao"
ENV_FILE="$REPO_DIR/.env"
VENV_PY="$REPO_DIR/venv/bin/python"

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

# Cores só quando é terminal de verdade
if [ -t 1 ]; then
    VERDE=$'\e[32m'; VERM=$'\e[31m'; AMAR=$'\e[33m'; NEG=$'\e[1m'; RESET=$'\e[0m'
else
    VERDE=""; VERM=""; AMAR=""; NEG=""; RESET=""
fi

falhas=0
avisos=0

titulo() { [ "$QUIET" -eq 1 ] || printf '\n%s%s%s\n' "$NEG" "$1" "$RESET"; }
ok()     { [ "$QUIET" -eq 1 ] || printf '  %s[ OK ]%s %s\n'  "$VERDE" "$RESET" "$1"; }
erro()   { printf '  %s[FALHA]%s %s\n' "$VERM" "$RESET" "$1"; falhas=$((falhas+1)); }
aviso()  { printf '  %s[AVISO]%s %s\n' "$AMAR" "$RESET" "$1"; avisos=$((avisos+1)); }

# Lê o valor de uma chave do .env (tudo após o primeiro '='), sem executar o
# arquivo. Remove eventual \r de finais de linha CRLF.
env_val() {
    [ -f "$ENV_FILE" ] || return 0
    grep -m1 "^${1}=" "$ENV_FILE" | cut -d= -f2- | tr -d '\r'
}

[ "$QUIET" -eq 1 ] || printf '\n%s=== Verificação do ambiente — Robô SIAFI (Descentralização) ===%s\n' "$NEG" "$RESET"

# ---------------------------------------------------------------------------
# 1. Repositório
# ---------------------------------------------------------------------------
titulo "[1] Repositório"
if [ -d "$REPO_DIR/.git" ]; then
    ok "repositório encontrado em $REPO_DIR"
else
    erro "repositório não encontrado em $REPO_DIR"
fi

# ---------------------------------------------------------------------------
# 2. Arquivos essenciais do fluxo
# ---------------------------------------------------------------------------
titulo "[2] Arquivos do robô"
for f in \
    consolida.py \
    siafi_automacao/descentralizacao.py \
    siafi_automacao/fluxo_anular_desc.py \
    siafi_automacao/fluxo_aprovar_desc.py \
    requirements.txt
do
    if [ -f "$REPO_DIR/$f" ]; then ok "$f"; else erro "faltando: $f"; fi
done

# ---------------------------------------------------------------------------
# 3. Ambiente virtual Python + dependências que o código realmente importa
# ---------------------------------------------------------------------------
titulo "[3] Ambiente Python (venv)"
if [ -x "$VENV_PY" ]; then
    ok "venv presente ($VENV_PY)"
    # py3270, pandas, openpyxl e dotenv são os imports de consolida.py /
    # descentralizacao.py. Consulta find_spec sem importar de fato (mais rápido).
    faltando=$("$VENV_PY" - <<'PY' 2>/dev/null
import importlib.util as u
mods = ["py3270", "pandas", "openpyxl", "dotenv"]
print(" ".join(m for m in mods if u.find_spec(m) is None))
PY
)
    rc=$?
    if [ $rc -ne 0 ]; then
        erro "o Python do venv não executou (venv corrompido? recrie com: python3 -m venv venv)"
    elif [ -n "$faltando" ]; then
        erro "dependências ausentes no venv: $faltando"
        aviso "  corrija com: cd \"$REPO_DIR\" && source venv/bin/activate && pip install -r requirements.txt"
    else
        ok "dependências importáveis (py3270, pandas, openpyxl, dotenv)"
    fi
else
    erro "venv não encontrado (crie com: cd \"$REPO_DIR\" && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt)"
fi

# ---------------------------------------------------------------------------
# 4. Binários do emulador 3270
# ---------------------------------------------------------------------------
titulo "[4] Emulador 3270"
for bin in s3270 x3270; do
    if command -v "$bin" >/dev/null 2>&1; then
        ok "$bin instalado"
    else
        erro "faltando: $bin (instale com: sudo apt install s3270 x3270)"
    fi
done

# ---------------------------------------------------------------------------
# 5. .env e variáveis obrigatórias
# ---------------------------------------------------------------------------
titulo "[5] Arquivo .env"
if [ -f "$ENV_FILE" ]; then
    ok ".env encontrado"
    # Todas obrigatórias: o código lê e usa cada uma. UNIDADE_ORCAMENTARIA é o
    # ponto cego do setup.sh (ele não grava essa chave) — por isso é checada aqui.
    for chave in USUARIO SENHA UNIDADE_EXECUTORA UNIDADE_ORCAMENTARIA PASTA_WINDOWS; do
        valor="$(env_val "$chave")"
        if [ -n "$valor" ]; then
            if [ "$chave" = "SENHA" ]; then
                ok "$chave definido (valor oculto)"
            else
                ok "$chave = $valor"
            fi
        else
            erro "$chave ausente ou vazio no .env"
        fi
    done
    # PASTA_LINUX é opcional (o código cai para <repo>/data se ela faltar)
    if [ -n "$(env_val PASTA_LINUX)" ]; then
        ok "PASTA_LINUX = $(env_val PASTA_LINUX)"
    else
        aviso "PASTA_LINUX não definida — o robô usará $REPO_DIR/data (ok na maioria dos casos)"
    fi
else
    erro ".env não encontrado em $ENV_FILE"
fi

# ---------------------------------------------------------------------------
# 6. Caminhos configurados realmente existem
# ---------------------------------------------------------------------------
titulo "[6] Caminhos configurados"
pasta_win="$(env_val PASTA_WINDOWS)"
pasta_lin="$(env_val PASTA_LINUX)"

if [ -n "$pasta_win" ]; then
    if [ -d "$pasta_win" ]; then
        ok "PASTA_WINDOWS acessível"
        # Subpastas fixas esperadas por consolida.py / descentralizacao.py
        while IFS= read -r sub; do
            if [ -d "$pasta_win/$sub" ]; then
                ok "  subpasta: $sub"
            else
                aviso "  subpasta ausente: $sub"
            fi
        done <<'SUBS'
Remanejados (Insira seu arquivo aqui)
Conferencia
Realizados/Remanejamento Realizados
Realizados/Conferencia Realizados
SUBS
    else
        erro "PASTA_WINDOWS não acessível: $pasta_win"
        aviso "  se estiver no OneDrive, confirme que a pasta está sincronizada/baixada localmente"
    fi
fi

if [ -n "$pasta_lin" ]; then
    if [ -d "$pasta_lin" ]; then
        ok "PASTA_LINUX acessível"
    else
        aviso "PASTA_LINUX ainda não existe: $pasta_lin (será criada na execução)"
    fi
fi

# ---------------------------------------------------------------------------
# 7. Interface gráfica (WSLg) — necessária só se usar Emulator(visible=True)
# ---------------------------------------------------------------------------
titulo "[7] Interface gráfica (WSLg)"
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    ok "WSLg disponível (DISPLAY=${DISPLAY:-}${WAYLAND_DISPLAY:+ WAYLAND_DISPLAY=$WAYLAND_DISPLAY})"
else
    aviso "WSLg não detectado — só é problema se o descentralizacao.py usar visible=True; nesse caso troque para visible=False"
fi

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
echo ""
if [ "$falhas" -eq 0 ]; then
    printf '%s%sAmbiente pronto — o robô pode ser executado.%s' "$NEG" "$VERDE" "$RESET"
    [ "$avisos" -gt 0 ] && printf ' %s(%d aviso(s) — não impeditivo(s))%s' "$AMAR" "$avisos" "$RESET"
    printf '\n\n'
    exit 0
else
    printf '%s%sForam encontradas %d pendência(s) [FALHA].%s Resolva os itens acima antes de rodar o robô.\n\n' \
        "$NEG" "$VERM" "$falhas" "$RESET"
    exit 1
fi
