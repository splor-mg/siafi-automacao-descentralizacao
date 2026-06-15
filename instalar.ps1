#Requires -Version 5.0

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

# ===========================================================================
# Rede: proxy do PRODEMGE + interceptacao SSL
# ===========================================================================
# Os downloads usam curl.exe (nativo do Windows 10/11), que lida bem com
# proxy que intercepta SSL - ao contrario do Invoke-WebRequest, que falha
# no handshake TLS ("conexao subjacente fechada / erro inesperado em envio").

$ProxyUrl          = "http://proxycamg.prodemge.gov.br:8080"
$script:ProxyCreds = $null    # guarda "usuario:senha" depois de perguntar uma vez

# URLs dos pacotes (atualize a versao do WSL aqui se sair uma nova).
# Se o proxy bloquear o dominio "blob.core.windows.net", troque a URL do
# Ubuntu por "https://aka.ms/wslubuntu" (segue redirect normalmente).
$WslPkgUrl    = "https://github.com/microsoft/WSL/releases/download/2.7.3/Microsoft.WSL_2.7.3.0_x64_ARM64.msixbundle"
$UbuntuPkgUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/Ubuntu2404-240425.AppxBundle"

# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

function Get-FileViaProxy {
    param([string]$Url, [string]$OutFile)

    # Pergunta as credenciais do proxy uma unica vez (cada pessoa informa as suas).
    if (-not $script:ProxyCreds) {
        Write-Host "  Informe as credenciais do proxy (individuais):" -ForegroundColor Yellow
        $u   = Read-Host "  Usuario do proxy (matricula)"
        $sec = Read-Host "  Senha do proxy (nao aparece)" -AsSecureString
        $b   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        $p   = [Runtime.InteropServices.Marshal]::PtrToStringAuto($b)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)
        # Senha vai em --proxy-user (nao em URL), entao @ e outros simbolos
        # nao precisam de codificacao.
        $script:ProxyCreds = "{0}:{1}" -f $u, $p
    }

    # curl.exe nativo do Windows. -L segue redirects | -k aceita o certificado
    # do proxy | -x define o proxy | --proxy-user envia usuario:senha | --fail
    # faz retornar erro em respostas HTTP 4xx/5xx.
    & curl.exe -L -k --fail -x $ProxyUrl --proxy-user $script:ProxyCreds -o $OutFile $Url

    if ($LASTEXITCODE -ne 0) {
        throw "Download falhou (curl codigo $LASTEXITCODE). Verifique usuario/senha do proxy, ou se o dominio esta liberado: $Url"
    }
    if (-not (Test-Path $OutFile)) {
        throw "Download nao gerou o arquivo: $OutFile"
    }
}

function Test-UbuntuRegistered {
    $distros = (wsl --list --quiet 2>$null) -replace '\x00', ''
    if ($LASTEXITCODE -ne 0) { return $false }
    return ($distros -join "`n") -match "ubuntu"
}

function Get-UbuntuDistroName {
    $distros = ((wsl --list --quiet 2>$null) -replace '\x00', '') -split "`r?`n" |
        Where-Object { $_ -match 'ubuntu' }
    $name = ($distros | Select-Object -First 1)
    if ($name) { return $name.Trim() } else { return "" }
}

function Test-WslEngineActive {
    wsl --status 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Test-SetupDone {
    param([string]$DistroName)
    wsl -d $DistroName -- bash -c "
        test -f ~/code/splor-mg/siafi-automacao-descentralizacao/.setup_done &&
        grep -q '^PASTA_WINDOWS=' ~/code/splor-mg/siafi-automacao-descentralizacao/.env 2>/dev/null
    " 2>$null
    return $LASTEXITCODE -eq 0
}

function Request-Elevation {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if (-not $isAdmin) {
        Write-Host "Solicitando permissao de administrador..." -ForegroundColor Yellow
        Start-Process PowerShell -Verb RunAs -ArgumentList `
            "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        exit 0
    }
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

function Enable-WslFeatures {
    Write-Host "Habilitando recursos do Windows (WSL + Plataforma de Maquina Virtual)..." -ForegroundColor Yellow
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null
}

function Install-WslAndUbuntu {
    $tmp       = $env:TEMP
    $wslPkg    = Join-Path $tmp "Microsoft.WSL.msixbundle"
    $ubuntuPkg = Join-Path $tmp "Ubuntu.appxbundle"

    # --- Motor do WSL ---
    if (-not (Get-AppxPackage -Name "*WindowsSubsystemForLinux*" -ErrorAction SilentlyContinue)) {
        Write-Host "Baixando o WSL (via proxy)..." -ForegroundColor Yellow
        Get-FileViaProxy $WslPkgUrl $wslPkg
        Write-Host "Instalando o WSL..." -ForegroundColor Yellow
        Add-AppxPackage -Path $wslPkg
    } else {
        Write-Host "Motor do WSL ja instalado." -ForegroundColor Gray
    }

    # --- Distro Ubuntu ---
    if (-not (Get-AppxPackage -Name "*Ubuntu*" -ErrorAction SilentlyContinue)) {
        Write-Host "Baixando o Ubuntu (via proxy - pode levar alguns minutos)..." -ForegroundColor Yellow
        Get-FileViaProxy $UbuntuPkgUrl $ubuntuPkg
        Write-Host "Instalando o Ubuntu..." -ForegroundColor Yellow
        Add-AppxPackage -Path $ubuntuPkg
    } else {
        Write-Host "Pacote do Ubuntu ja instalado." -ForegroundColor Gray
    }

    wsl --set-default-version 2 2>$null | Out-Null
}

function Initialize-Ubuntu {
    # Primeira execucao da distro: extrai o rootfs e cria o usuario Linux (interativo).
    Write-Host ""
    Write-Host "Inicializando o Ubuntu pela primeira vez." -ForegroundColor Cyan
    Write-Host "Crie um usuario e senha do Linux quando solicitado." -ForegroundColor Cyan
    Write-Host "(NAO precisa ser igual ao login do Windows)" -ForegroundColor Gray
    Write-Host ""

    $pkg = Get-AppxPackage -Name "*Ubuntu*" | Sort-Object Version -Descending | Select-Object -First 1
    if ($null -eq $pkg) {
        Write-Host "ERRO: pacote do Ubuntu nao encontrado." -ForegroundColor Red
        exit 1
    }

    $launcher = Get-ChildItem -Path $pkg.InstallLocation -Filter "ubuntu*.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($null -eq $launcher) {
        Write-Host "ERRO: nao encontrei o executavel de inicializacao do Ubuntu." -ForegroundColor Red
        Write-Host "Abra o Ubuntu manualmente uma vez (menu Iniciar) e rode instalar.bat de novo." -ForegroundColor Red
        exit 1
    }

    & $launcher.FullName
}

# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "=== Instalacao e Configuracao do Robo SIAFI (Descentralizacao) ===" -ForegroundColor Cyan
Write-Host ""

# Fase 1: instalar WSL + Ubuntu se a distro ainda nao esta registrada
if (-not (Test-UbuntuRegistered)) {

    Request-Elevation                       # a partir daqui, rodando como administrador

    $wslJaAtivo = Test-WslEngineActive
    Enable-WslFeatures
    Install-WslAndUbuntu

    if (-not $wslJaAtivo) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host "  WSL e Ubuntu instalados com sucesso!"                       -ForegroundColor Green
        Write-Host "  REINICIE o Windows e execute instalar.bat novamente."       -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Green
        exit 0
    }

    # WSL ja estava funcional nesta sessao -> cria o usuario e registra a distro agora.
    Initialize-Ubuntu

    if (-not (Test-UbuntuRegistered)) {
        Write-Host ""
        Write-Host "ERRO: o Ubuntu nao foi registrado. Abra o Ubuntu manualmente uma vez e rode instalar.bat de novo." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "Ubuntu registrado. Prosseguindo com a configuracao..." -ForegroundColor Green
    Write-Host ""
}

# Nome real da distro (pode ser "Ubuntu" ou "Ubuntu-24.04")
$Distro = Get-UbuntuDistroName
if ([string]::IsNullOrWhiteSpace($Distro)) { $Distro = "Ubuntu" }

# Fase 2: rodar setup.sh se ainda nao configurado
if (-not (Test-SetupDone $Distro)) {
    Write-Host "Configurando o ambiente Ubuntu ($Distro)..." -ForegroundColor Yellow
    Write-Host "(Isso pode levar alguns minutos)" -ForegroundColor Gray
    Write-Host ""

    $setupWin = Join-Path $PSScriptRoot "setup.sh"
    $setupWsl = ConvertTo-WslPath $setupWin

    wsl -d $Distro -- bash -c "bash '$setupWsl'"

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