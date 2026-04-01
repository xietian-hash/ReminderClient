param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if ($Clean) {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Filter '*.spec' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name ReminderClient `
    --icon assets\app_icon.ico `
    --add-data "assets\app_icon.ico;assets" `
    --add-data "assets\app_icon.png;assets" `
    --paths src `
    --hidden-import PySide6.QtCore `
    --hidden-import PySide6.QtGui `
    --hidden-import PySide6.QtWidgets `
    --hidden-import PySide6.QtMultimedia `
    src\reminder_client\main.py
