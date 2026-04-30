# deploy_to_rpi.ps1
# Nasadí potify na Raspberry Pi 3 (10.0.0.3) přes SSH s Pageant
# Předpoklad: plink.exe a pscp.exe jsou v PATH (PuTTY), Pageant běží s klíčem

param(
    [string]$RpiHost = "10.0.0.3",
    [string]$RpiUser = "pi",
    [string]$RemoteDir = "/home/pi/potify",
    [int]$Port = 50555
)

$ProjectDir = $PSScriptRoot
$SshTarget = "${RpiUser}@${RpiHost}"

# Ověř dostupnost plink / pscp
foreach ($tool in @("plink", "pscp")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Error "$tool nebyl nalezen v PATH. Nainstaluj PuTTY a přidej ho do PATH."
        exit 1
    }
}

Write-Host "==> Vytvářím adresář $RemoteDir na RPi..."
plink -batch $SshTarget "mkdir -p $RemoteDir"
if ($LASTEXITCODE -ne 0) { Write-Error "SSH spojení selhalo."; exit 1 }

Write-Host "==> Kopíruji projekt na RPi (vynechávám .venv, .git, __pycache__, output)..."

# Soubory a složky ke kopírování
$items = @("src", "tests", "pyproject.toml", "README.md", "potify.service", "setup_rpi.sh")

foreach ($item in $items) {
    $localPath = Join-Path $ProjectDir $item
    if (Test-Path $localPath) {
        Write-Host "    Kopíruji: $item"
        if (Test-Path $localPath -PathType Container) {
            pscp -batch -r $localPath "${SshTarget}:${RemoteDir}/"
        } else {
            pscp -batch $localPath "${SshTarget}:${RemoteDir}/"
        }
        if ($LASTEXITCODE -ne 0) { Write-Error "Kopírování $item selhalo."; exit 1 }
    }
}

Write-Host "==> Spouštím setup skript na RPi (může trvat 15-30 minut kvůli kompilaci Pythonu)..."
plink -batch $SshTarget "chmod +x $RemoteDir/setup_rpi.sh && bash $RemoteDir/setup_rpi.sh"
if ($LASTEXITCODE -ne 0) { Write-Error "Setup skript selhal."; exit 1 }

Write-Host ""
Write-Host "==> Hotovo! Aplikace beží na http://${RpiHost}:${Port}"
