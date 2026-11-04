$o = Join-Path $PSScriptRoot "tailscale_status.txt"
$r = @()
$exe = @("C:\Program Files\Tailscale\tailscale.exe", "C:\Program Files (x86)\Tailscale\tailscale.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) { $c = Get-Command tailscale -ErrorAction SilentlyContinue; if ($c) { $exe = $c.Source } }
$r += "EXE: $exe"
if ($exe) {
  $r += "--- status ---"
  $r += (& $exe status 2>&1)
  $r += "--- ip ---"
  $r += (& $exe ip -4 2>&1)
  $r += "--- dns ---"
  $r += (& $exe status --json 2>&1 | Select-String '"DNSName"' | Select-Object -First 1)
  $r += "--- serve ---"
  $r += (& $exe serve status 2>&1)
}
$r | Out-File $o -Encoding utf8
