$o = Join-Path $PSScriptRoot "tailscale_serve.txt"
$exe = "C:\Program Files\Tailscale\tailscale.exe"
$r = @()
$r += "--- serve ---"
$job = Start-Job { param($e) & $e serve --bg http://127.0.0.1:8765 2>&1 } -ArgumentList $exe
if (Wait-Job $job -Timeout 25) { $r += (Receive-Job $job) } else { $r += "(sem resposta em 25 s — talvez esteja esperando ativar HTTPS no painel)"; $r += (Receive-Job $job); Stop-Job $job }
$r += "--- serve status ---"
$r += (& $exe serve status 2>&1)
$r | Out-File $o -Encoding utf8
