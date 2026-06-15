#Requires -Version 5.0

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

function Get-UbuntuDistroName {
    $distros = ((wsl --list --quiet 2>$null) -replace '\x00', '') -split "`r?`n" |
        Where-Object { $_ -match 'ubuntu' }
    $name = ($distros | Select-Object -First 1)
    if ($name) { return $name.Trim() } else { return "" }
}

function Test-SetupDone {
    param([string]$DistroName)
    wsl -d $DistroName -- bash -c "
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

# Nome real da distro (pode ser "Ubuntu" ou "Ubuntu-24.04")
$Distro = Get-UbuntuDistroName
if ([string]::IsNullOrWhiteSpace($Distro)) { $Distro = "Ubuntu" }

if (-not (Test-SetupDone $Distro)) {
    Write-Host "ERRO: ambiente nao configurado." -ForegroundColor Red
    Write-Host "Execute instalar.bat antes de rodar o robo." -ForegroundColor Yellow
    exit 1
}

# Atualiza o robo (git pull) para que toda alteracao do fluxo se propague a
# todos os computadores. Falha de rede/git nao impede a execucao com a versao local.
Write-Host "Atualizando o robo (git pull)..." -ForegroundColor Cyan
wsl -d $Distro -- bash -c "cd ~/code/splor-mg/siafi-automacao-descentralizacao && git pull --ff-only 2>&1 || echo '[aviso] Nao foi possivel atualizar (git pull); seguindo com a versao local.'"

Write-Host "Trazendo as planilhas do OneDrive e consolidando..." -ForegroundColor Cyan
wsl -d $Distro -- bash -c "cd ~/code/splor-mg/siafi-automacao-descentralizacao && source venv/bin/activate && PYTHONIOENCODING=utf-8 python consolida.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "A consolidacao encerrou com erro (codigo $LASTEXITCODE). O robo nao sera iniciado." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Iniciando o robo SIAFI (descentralizacao)..." -ForegroundColor Cyan
wsl -d $Distro -- bash -c "cd ~/code/splor-mg/siafi-automacao-descentralizacao && source venv/bin/activate && PYTHONIOENCODING=utf-8 python siafi_automacao/descentralizacao.py"
$codigo = $LASTEXITCODE

# Codigo 3 = senha do SIAFI expirada: abre o .env para o usuario salvar a nova senha
if ($codigo -eq 3) {
    Write-Host ""
    Write-Host "Senha expirada. Abra o SIAFI manualmente e atualize sua senha." -ForegroundColor Yellow
    Write-Host "Vou abrir o arquivo .env para voce salvar a nova senha (campo SENHA)." -ForegroundColor Yellow
    Write-Host "Depois de salvar o .env, rode o robo novamente." -ForegroundColor Yellow

    $envWin = wsl -d $Distro -- bash -c 'wslpath -w "$HOME/code/splor-mg/siafi-automacao-descentralizacao/.env"'
    if ($envWin) {
        Start-Process notepad.exe -ArgumentList ($envWin.Trim())
    } else {
        Write-Host "[aviso] Nao consegui localizar o .env automaticamente." -ForegroundColor Red
    }
    exit $codigo
}

if ($codigo -ne 0) {
    Write-Host ""
    Write-Host "O robo encerrou com erro (codigo $codigo)." -ForegroundColor Red
}

exit $codigo