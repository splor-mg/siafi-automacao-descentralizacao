#Requires -Version 5.0

# -JaAtualizado e usado apenas pela auto-atualizacao (ver Update-Lancador), para
# garantir que o script se relance no maximo UMA vez por execucao.
param([switch]$JaAtualizado)

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

function Get-TextoNormalizado {
    # Compara conteudo ignorando diferencas de fim de linha (o repositorio usa LF,
    # o Windows pode gravar CRLF) e espacos/quebras no final do arquivo. Sem isso a
    # comparacao acusaria diferenca em toda execucao.
    param([string]$Texto)
    return ($Texto -replace "`r`n", "`n").TrimEnd()
}

function Update-Lancador {
    <#
      O robo.ps1 e o unico arquivo do projeto que roda FORA do WSL: ele mora em
      %LOCALAPPDATA% (extraido do .exe) e e justamente quem dispara o "git pull".
      Por isso o git pull atualiza todo o resto (consolida.py, descentralizacao.py,
      fluxos) mas nunca ele proprio.

      Esta funcao fecha essa lacuna: depois do git pull, compara a copia que esta
      rodando com a do repositorio e, se mudou, se sobrescreve e relanca. Assim o
      .exe nao precisa ser regerado a cada alteracao do robo.ps1.

      Falhar aqui NUNCA pode impedir o robo de rodar - qualquer erro so vira aviso.
      Devolve $true quando ja relancou (o chamador deve encerrar).
    #>
    param([string]$DistroName)

    if ($JaAtualizado) { return $false }   # trava contra relancamento em loop

    try {
        $caminhoRepo = wsl -d $DistroName -- bash -c 'wslpath -w "$HOME/code/splor-mg/siafi-automacao-descentralizacao/robo.ps1"' 2>$null
        if (-not $caminhoRepo) { return $false }
        $caminhoRepo = $caminhoRepo.Trim()
        if (-not (Test-Path -LiteralPath $caminhoRepo)) { return $false }

        $doRepo = Get-Content -LiteralPath $caminhoRepo -Raw -ErrorAction Stop
        $atual  = Get-Content -LiteralPath $PSCommandPath -Raw -ErrorAction Stop

        if ((Get-TextoNormalizado $doRepo) -eq (Get-TextoNormalizado $atual)) {
            return $false   # ja esta na versao mais recente
        }

        Write-Host "Atualizando o proprio lancador (robo.ps1)..." -ForegroundColor Cyan
        # UTF8 sem BOM, para o arquivo continuar identico ao do repositorio.
        $semBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($PSCommandPath, $doRepo, $semBom)
    }
    catch {
        Write-Host "[aviso] Nao foi possivel atualizar o lancador; seguindo com a versao local." -ForegroundColor Yellow
        Write-Host "        ($($_.Exception.Message))" -ForegroundColor DarkGray
        return $false
    }

    # Relanca em um processo NOVO, do mesmo jeito que o robo.bat faz. Isso garante
    # que o codigo recem-gravado seja o que roda (o processo atual ja tem a versao
    # antiga carregada em memoria) e que o codigo de saida chegue intacto ao .bat.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -JaAtualizado
    return $true
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

# O git pull acima nao alcanca este proprio arquivo (ver Update-Lancador).
if (Update-Lancador $Distro) { exit $LASTEXITCODE }

Write-Host "Trazendo as planilhas do OneDrive e consolidando..." -ForegroundColor Cyan
wsl -d $Distro -- bash -c "cd ~/code/splor-mg/siafi-automacao-descentralizacao && source venv/bin/activate && PYTHONIOENCODING=utf-8 python consolida.py"
$codigoConsolida = $LASTEXITCODE

# Codigo 2 = nada a consolidar (pasta "Remanejados" vazia). Nao e erro, mas o robo
# tambem nao pode seguir: sem consolidado novo ele reprocessaria a conferencia
# anterior, refazendo no SIAFI operacoes que ja foram feitas.
if ($codigoConsolida -eq 2) {
    Write-Host ""
    Write-Host "Nenhuma planilha nova para processar. O robo nao sera iniciado." -ForegroundColor Yellow
    Write-Host "Coloque os arquivos na pasta 'Remanejados (Insira seu arquivo aqui)' e rode de novo." -ForegroundColor Yellow
    exit 0
}

if ($codigoConsolida -ne 0) {
    Write-Host ""
    Write-Host "A consolidacao encerrou com erro (codigo $codigoConsolida). O robo nao sera iniciado." -ForegroundColor Red
    Write-Host "Corrija os itens listados acima nas planilhas e rode de novo." -ForegroundColor Yellow
    exit $codigoConsolida
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