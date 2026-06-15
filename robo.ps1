#Requires -Version 5.0

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

function Test-SetupDone {
    wsl -d Ubuntu -- bash -c "
        test -f ~/code/splor-mg/siafi-automacao-descentralizacao/.setup_done &&
        grep -q '^PASTA_WINDOWS=' ~/code/splor-mg/siafi-automacao-descentralizacao/.env 2>/dev/null
    " 2>$null
    return $LASTEXITCODE -eq 0
}

# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "=== Robo SIAFI ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-SetupDone)) {
    Write-Host "ERRO: ambiente nao configurado." -ForegroundColor Red
    Write-Host "Execute instalar.bat antes de rodar o robo." -ForegroundColor Yellow
    exit 1
}

Write-Host "Trazendo as planilhas do OneDrive e consolidando..." -ForegroundColor Cyan
wsl -d Ubuntu -- bash -c "cd ~/code/splor-mg/siafi-automacao-descentralizacao && source venv/bin/activate && PYTHONIOENCODING=utf-8 python consolida.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "A consolidacao encerrou com erro (codigo $LASTEXITCODE). O robo nao sera iniciado." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Iniciando o robo SIAFI (descentralizacao)..." -ForegroundColor Cyan
wsl -d Ubuntu -- bash -c "cd ~/code/splor-mg/siafi-automacao-descentralizacao && source venv/bin/activate && PYTHONIOENCODING=utf-8 python siafi_automacao/descentralizacao.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "O robo encerrou com erro (codigo $LASTEXITCODE)." -ForegroundColor Red
}

exit $LASTEXITCODE
