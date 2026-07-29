#Requires -Version 5.0

# Roda o diagnóstico de pré-requisitos (verificar.sh) dentro do WSL e devolve
# o mesmo código de saída (0 = pronto, 1 = há pendências). É o mesmo verificador
# que o robo.ps1 usa como porteiro — aqui você o executa avulso, com saída completa.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

function Get-UbuntuDistroName {
    $distros = ((wsl --list --quiet 2>$null) -replace '\x00', '') -split "`r?`n" |
        Where-Object { $_ -match 'ubuntu' }
    $name = ($distros | Select-Object -First 1)
    if ($name) { return $name.Trim() } else { return "" }
}

$Distro = Get-UbuntuDistroName
if ([string]::IsNullOrWhiteSpace($Distro)) { $Distro = "Ubuntu" }

wsl -d $Distro -- bash -c "
    cd ~/code/splor-mg/siafi-automacao-descentralizacao 2>/dev/null || {
        echo 'ERRO: repositório não encontrado em ~/code/splor-mg/siafi-automacao-descentralizacao'
        exit 1
    }
    if [ -f verificar.sh ]; then
        bash verificar.sh
    else
        echo 'ERRO: verificar.sh não está no repositório. Coloque-o na raiz do repo (e faça commit para propagar via git pull).'
        exit 1
    fi
"
exit $LASTEXITCODE
