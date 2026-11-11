#Requires -Version 5.0

# Roda o diagnostico de pre-requisitos (verificar.sh) dentro do WSL e devolve
# o mesmo codigo de saida (0 = pronto, 1 = ha pendencias). E o mesmo verificador
# que o robo.ps1 usa como porteiro; aqui ele e executado avulso, com saida completa.
#
# SEM ACENTOS neste arquivo, de proposito: o PowerShell 5.1 le o .ps1 como
# Windows-1252 e corrompe os caracteres acentuados das mensagens.

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
        echo 'ERRO: repositorio nao encontrado em ~/code/splor-mg/siafi-automacao-descentralizacao'
        exit 1
    }
    if [ -f verificar.sh ]; then
        bash verificar.sh
    else
        echo 'ERRO: verificar.sh nao esta no repositorio. Atualize o repositorio com git pull.'
        exit 1
    fi
"
exit $LASTEXITCODE
