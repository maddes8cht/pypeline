:: cmdfzf.cmd - FZF wrapper for CMD scripts
:: use [ctrl]-b to switch to bat preview and [ctrl]-c to switch back to cmdlist preview
:: Parameters: query
:: Example: cmdfzf.cmd git
@echo off
setlocal enabledelayedexpansion
set "CMDDIR=C:\PAP\cmd"

if not exist "%CMDDIR%" (
    echo Error: Directory %CMDDIR% does not exist!
    exit /b 1
)

:: Set query parameters if given
set "FZF_QUERY="
if not "%~1"=="" set "FZF_QUERY=--query=%~1"

:: FZF with preview and switching functionality
cd /d "%CMDDIR%"
for /f "delims=" %%F in ('
    dir /b *.cmd ^| awk "{sub(/\.cmd$/,\"\"); print}" ^|
    fzf %FZF_QUERY% --preview "cmdlist /c {}" --preview-window right:60%% ^
        --bind "ctrl-b:change-preview(bat --style=plain --color=always --line-range=:50 {}.cmd)" ^
        --bind "ctrl-c:change-preview(cmdlist /c {})"
') do (
    echo Running %%F.cmd...
    call "%%F.cmd"
)

endlocal
