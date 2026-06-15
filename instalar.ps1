#Requires -Version 5.0

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

function Test-UbuntuInstalled {
    $distros = (wsl --list --quiet 2>$null) -replace '\x00', ''
    if ($LASTEXITCODE -ne 0) { return $false }
    return ($distros -join "`n") -match "ubuntu"
}

function Test-SetupDone {
    wsl -d Ubuntu -- bash -c "
        test -f ~/code/splor-mg/siafi-automacao-descentralizacao/.setup_done &&
        grep -q '^PASTA_WINDOWS=' ~/code/splor-mg/siafi-automacao-descentralizacao/.env 2>/dev/null
    " 2>$null
    return $LASTEXITCODE -eq 0
}

function Request-Elevation {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if (-not $isAdmin) {
        Write-Host "Solicitando permissao de administrador para instalar o WSL..."
        Start-Process PowerShell -Verb RunAs -ArgumentList `
            "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        exit 0
    }
}

function Test-WslEngineActive {
    wsl --status 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function ConvertTo-WslPath {
    param([string]$WindowsPath)

    if ($WindowsPath -match '^\\\\wsl\.localhost\\[^\\]+\\(.*)$') {
        return '/' + $Matches[1].Replace('\', '/')
    }

    if ($WindowsPath -match '^\\\\') {
        throw "ConvertTo-WslPath: caminho UNC nao suportado: $WindowsPath"
    }

    $drive = $WindowsPath[0].ToString().ToLower()
    $rest  = $WindowsPath.Substring(2).Replace('\', '/')
    return "/mnt/$drive$rest"
}

# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "=== Instalacao e Configuracao do Robo SIAFI ===" -ForegroundColor Cyan
Write-Host ""

# Fase 1: Ubuntu nao registrado no WSL
if (-not (Test-UbuntuInstalled)) {
    $wslJaAtivo = Test-WslEngineActive

    if ($wslJaAtivo) {
        Write-Host "WSL ja instalado, mas Ubuntu nao encontrado. Registrando Ubuntu..." -ForegroundColor Yellow
    } else {
        Write-Host "WSL nao encontrado. Instalando WSL e Ubuntu..." -ForegroundColor Yellow
    }

    Request-Elevation

    Write-Host "Executando: wsl --install -d Ubuntu" -ForegroundColor Yellow
    wsl --install -d Ubuntu

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERRO: wsl --install falhou (codigo $LASTEXITCODE)." -ForegroundColor Red
        Write-Host "Verifique se a virtualizacao esta habilitada na BIOS e tente novamente." -ForegroundColor Red
        exit 1
    }

    if (-not $wslJaAtivo) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host "  WSL e Ubuntu instalados com sucesso!"                       -ForegroundColor Green
        Write-Host "  REINICIE o Windows e execute instalar.bat novamente."       -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Green
        exit 0
    }

    Write-Host ""
    Write-Host "Ubuntu registrado. Prosseguindo com a configuracao..." -ForegroundColor Green
    Write-Host ""
}

# Fase 2: Ubuntu instalado mas projeto nao configurado
if (-not (Test-SetupDone)) {
    Write-Host "Configurando o ambiente Ubuntu..." -ForegroundColor Yellow
    Write-Host "(Isso pode levar alguns minutos)" -ForegroundColor Gray
    Write-Host ""

    $setupWin = Join-Path $PSScriptRoot "setup.sh"
    $setupWsl = ConvertTo-WslPath $setupWin

    wsl -d Ubuntu -- bash -c "bash '$setupWsl'"

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERRO: setup.sh falhou (codigo $LASTEXITCODE). Verifique as mensagens acima." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  Configuracao concluida!"                                     -ForegroundColor Green
    Write-Host "  Execute robo.bat para iniciar a automacao."                  -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    exit 0
}

Write-Host "Ambiente ja configurado. Nada a fazer." -ForegroundColor Green
Write-Host "Execute robo.bat para iniciar a automacao." -ForegroundColor Gray
