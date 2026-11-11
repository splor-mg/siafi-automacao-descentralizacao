; ---------------------------------------------------------------------------
; Script de build do "Automação_Descentralização.exe"
;
; O .exe NAO e um programa compilado: e um autoextrator NSIS que serve de atalho
; clicavel para o robo. Ele faz exatamente tres coisas:
;
;   1. cria %LOCALAPPDATA%\SEPLAG-MG\SIAFI-Automacao-Descentralizacao
;   2. extrai ali dentro o robo.bat e o robo.ps1
;   3. executa o robo.bat, que chama o robo.ps1, que dispara o fluxo no WSL
;
; Ele NAO instala nada: em uma maquina sem o ambiente pronto (WSL/Ubuntu,
; repositorio, venv, .env), o robo.ps1 lista o que falta - a mesma checagem do
; verificar.bat - e nao inicia o robo.
;
; ---------------------------------------------------------------------------
; COMO GERAR O .EXE (precisa ser no Windows)
;
;   1. Instale o NSIS 3.x: https://nsis.sourceforge.io/Download
;   2. Clique com o botao direito neste arquivo -> "Compile NSIS Script"
;      ou, pelo terminal:
;          "C:\Program Files (x86)\NSIS\makensis.exe" instalador.nsi
;   3. O "Automação_Descentralização.exe" aparece nesta mesma pasta.
;
; ---------------------------------------------------------------------------
; QUANDO REGERAR
;
; Desde que o robo.ps1 passou a se auto-atualizar (funcao Update-Lancador), na
; pratica NUNCA: o robo.ps1 se compara com a copia do repositorio depois do
; "git pull" e se sobrescreve sozinho quando ela muda.
;
; Regere apenas se mudar algo que a auto-atualizacao nao alcanca: o robo.bat, o
; caminho de instalacao, ou a propria funcao Update-Lancador de um jeito que
; quebre a comparacao.
; ---------------------------------------------------------------------------

Unicode true
SetCompressor /SOLID lzma

!define NOME_CURTO "SIAFI-Automacao-Descentralizacao"
!define FABRICANTE "SEPLAG-MG"
!define VERSAO      "1.1.0.0"

Name          "Automação Descentralização"
OutFile       "Automação_Descentralização.exe"
InstallDir    "$LOCALAPPDATA\${FABRICANTE}\${NOME_CURTO}"

; Instala na pasta do usuario, entao nao precisa de administrador.
RequestExecutionLevel user

; Sem assistente: o usuario da duplo clique e o robo comeca. As duas linhas
; abaixo sao o que faz o .exe se comportar como um atalho, e nao como um
; instalador com telas de "Avancar / Avancar / Concluir".
SilentInstall silent
ShowInstDetails nevershow

; Informacoes de versao. Alem de identificar a origem do arquivo, ajudam o
; SmartScreen e os antivirus a tratarem o .exe com menos desconfianca.
VIProductVersion "${VERSAO}"
VIAddVersionKey  "ProductName"     "Automação Descentralização"
VIAddVersionKey  "FileDescription" "Atalho para o robô de descentralização de cota orçamentária (SIAFI)"
VIAddVersionKey  "CompanyName"     "SEPLAG-MG / DCMEFO"
VIAddVersionKey  "LegalCopyright"  "SEPLAG-MG"
VIAddVersionKey  "FileVersion"     "${VERSAO}"
VIAddVersionKey  "ProductVersion"  "${VERSAO}"

Section "Principal"
    SetOutPath "$INSTDIR"

    ; Sobrescreve sempre: a copia extraida e descartavel, a fonte da verdade e
    ; o repositorio dentro do WSL.
    SetOverwrite on
    File "robo.bat"
    File "robo.ps1"

    ; Passa o bastao para o fluxo normal. Exec (e nao ExecWait) porque o .exe nao
    ; precisa sobreviver ao robo: o robo.bat tem o proprio "pause" e segura a
    ; janela aberta ate o usuario ler o resultado.
    Exec '"$INSTDIR\robo.bat"'
SectionEnd
