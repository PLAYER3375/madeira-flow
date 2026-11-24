$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$candidatos = @('python3.14.exe', 'python3.13.exe', 'python.exe', 'python3.exe', 'py.exe')
$interpretador = $null
$prefixo = @()
foreach ($candidato in $candidatos) {
    $comando = Get-Command $candidato -ErrorAction SilentlyContinue
    if (-not $comando) { continue }
    $testePrefixo = @()
    if ($candidato -eq 'py.exe') { $testePrefixo = @('-3') }
    try {
        & $comando.Source @testePrefixo -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $interpretador = $comando.Source
            $prefixo = $testePrefixo
            break
        }
    } catch { continue }
}
if (-not $interpretador) {
    Write-Host 'Instale Python 3.11 ou superior com Tcl/Tk e adicione-o ao PATH.'
    exit 1
}
if ($args.Count -gt 0 -and $args[0] -eq '--testes') {
    & $interpretador @prefixo -X utf8 scripts/verificar.py
} elseif ($args.Count -gt 0 -and $args[0] -eq '--empacotar') {
    & $interpretador @prefixo -X utf8 scripts/empacotar.py
} else {
    & $interpretador @prefixo -X utf8 -m madeiraflow @args
}
exit $LASTEXITCODE
